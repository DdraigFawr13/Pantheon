"""The turn loop (architecture section 3): tools on an uncommitted simulation, then checked prose."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from pantheon.engine.rng import RngStreams
from pantheon.engine.state import EventRecord, GameState
from pantheon.engine.timeline import Rules, Simulation
from pantheon.engine.tools import apply_tool, tool_definition, tool_definitions
from pantheon.llm.client import LLMClient, LLMReply, LLMUnavailable
from pantheon.narrator import fallback
from pantheon.narrator.assemble import assemble
from pantheon.narrator.validators import prose_problems, strip_action_list
from pantheon.world.loader import World

_SUGGEST_PROMPT = (
    "Now call suggest_actions with 3 to 5 next actions for the player. Include a non-violent action "
    "and one with a visible cost or risk in its cost field. Use no digits. Write no more prose."
)
_PROSE_ONLY = "Write the narration of this turn now, in prose, with no tools."


@dataclass
class TurnOutcome:
    narration: str
    is_fallback: bool
    events: list[EventRecord]
    rng_state: dict[str, Any]
    state: GameState
    tokens_in: int = 0
    tokens_cached: int = 0
    tokens_out: int = 0
    log: list[str] = field(default_factory=list)


def _numbers_in(value: Any) -> set[int]:
    if isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {value}
    if isinstance(value, dict):
        return set().union(*(_numbers_in(v) for v in value.values())) if value else set()
    return set()


class _Turn:
    def __init__(
        self, client: LLMClient, sim: Simulation, max_retries: int, system: list[dict[str, Any]]
    ) -> None:
        self.client = client
        self.sim = sim
        self.max_retries = max_retries
        self.system = system
        self.rejections: Counter[str] = Counter()
        self.allowed: set[int] = set()
        self.tokens = [0, 0, 0]
        self.log: list[str] = []

    def call(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> LLMReply:
        reply = self.client.complete(self.system, messages, tools)
        self.tokens = [
            self.tokens[0] + reply.tokens_in,
            self.tokens[1] + reply.tokens_cached,
            self.tokens[2] + reply.tokens_out,
        ]
        return reply

    def run_tools(self, reply: LLMReply) -> list[dict[str, Any]]:
        """Apply each call and build its result. A call rejected too often is dropped and logged (NAR-06)."""
        results = []
        for call in reply.tool_calls:
            if self.rejections[call.name] >= self.max_retries:
                self.sim.emit("tool_call_dropped", {"tool": call.name, "args": call.args})
                self.log.append(f"dropped {call.name}")
                payload: dict[str, Any] = {
                    "status": "dropped",
                    "reason": "too many rejections; carry on without it",
                }
            else:
                result = apply_tool(self.sim, call.name, call.args)
                payload = result.payload()
                if result.accepted:
                    self.allowed |= _numbers_in(result.data)
                    self.log.append(f"ok {call.name}")
                else:
                    self.rejections[call.name] += 1
                    self.log.append(f"rejected {call.name}: {result.reason}")
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(payload)})
        return results

    def checked(self, text: str) -> list[str]:
        return ["the reply is empty"] if not text else prose_problems(text, self.allowed)

    def narrate(self, messages: list[dict[str, Any]], rounds: int) -> str | None:
        """Run tool rounds until valid prose. None means the fallback text must be used."""
        written: list[str] = []
        for _ in range(rounds):
            reply = self.call(messages, tool_definitions())
            text = strip_action_list(reply.text).strip()
            if text:
                written.append(text)
            if reply.tool_calls:
                messages += [
                    {"role": "assistant", "content": reply.blocks()},
                    {"role": "user", "content": self.run_tools(reply)},
                ]
                continue
            narration = "\n\n".join(written)
            problems = self.checked(narration)
            if not problems:
                return narration
            self.log.append("rejected prose: " + "; ".join(problems))
            if self.rejections["prose"] >= self.max_retries:
                return None
            self.rejections["prose"] += 1
            written = []
            messages += [
                {"role": "assistant", "content": reply.blocks() or [{"type": "text", "text": "(no reply)"}]},
                {
                    "role": "user",
                    "content": "That narration was not shown, because "
                    + "; ".join(problems)
                    + ". Write the whole narration again without that.",
                },
            ]
        # The round cap: prose already written may stand; else one call with no tools (NAR-07).
        narration = "\n\n".join(written)
        if narration and not self.checked(narration):
            return narration
        messages.append({"role": "user", "content": _PROSE_ONLY})
        text = strip_action_list(self.call(messages, None).text).strip()
        return None if self.checked(text) else text

    def suggest(self, messages: list[dict[str, Any]], narration: str) -> None:
        """Ask for actions when the model skipped them (D-030). The prose already stands."""
        messages += [
            {"role": "assistant", "content": [{"type": "text", "text": narration}]},
            {"role": "user", "content": _SUGGEST_PROMPT},
        ]
        tools = [tool_definition("suggest_actions")]
        for _ in range(self.max_retries + 1):
            reply = self.call(messages, tools)
            if not reply.tool_calls:
                return
            messages += [
                {"role": "assistant", "content": reply.blocks()},
                {"role": "user", "content": self.run_tools(reply)},
            ]
            if self.sim.suggested:
                return


def take_turn(
    client: LLMClient,
    world: World,
    rules: Rules,
    state: GameState,
    rng_state: dict[str, Any],
    recent: list[tuple[str, str]],
    player_input: str,
    turn: int,
    *,
    max_rounds: int = 6,
    max_retries: int = 2,
    violence: str = "moderate",
) -> TurnOutcome:
    """Play one turn without touching storage. The caller commits the outcome atomically (OPS-03)."""
    rng = RngStreams.from_state(rng_state)
    sim = Simulation(state, rng, rules, turn)
    system, messages = assemble(state, world, recent, player_input, violence)
    run = _Turn(client, sim, max_retries, system)
    narration: str | None = None
    try:
        narration = run.narrate(messages, max_rounds)
        if narration is not None and not sim.suggested:
            run.suggest(messages, narration)
    except LLMUnavailable as exc:
        run.log.append(f"model unavailable: {exc}")
    return TurnOutcome(
        narration=narration if narration is not None else fallback.render(sim),
        is_fallback=narration is None,
        events=sim.events,
        rng_state=rng.state(),
        state=sim.state,
        tokens_in=run.tokens[0],
        tokens_cached=run.tokens[1],
        tokens_out=run.tokens[2],
        log=run.log,
    )
