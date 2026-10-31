"""The turn loop: referee, then narrator, then scribe, on an uncommitted simulation (D-031).

Small local models skip tools when given a long list and free choice, so the engine runs the order:
a referee call that may only roll, a prose call that must narrate the result, and a scribe call that
records consequences. Nothing is committed here; a failed call never corrupts the log (OPS-03).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from pantheon.engine.rng import RngStreams
from pantheon.engine.state import EventRecord, GameState
from pantheon.engine.timeline import Rules, Simulation
from pantheon.engine.tools import ToolResult, apply_tool, tool_definitions
from pantheon.llm.client import LLMClient, LLMReply, LLMUnavailable
from pantheon.narrator import fallback
from pantheon.narrator.assemble import assemble, state_view
from pantheon.narrator.notices import CHECK_MARKER, place_notices
from pantheon.narrator.validators import prose_problems, repeats_earlier_turn, strip_action_list
from pantheon.world.loader import World

_REFEREE_PROMPT = (
    "[Referee step, no story yet. If the player is attempting something physical, risky, stealthy, forceful "
    "or deceptive whose result is not certain, call request_check now and choose the stat, difficulty and "
    "challenge_tier. If the action names a stat in brackets, use that stat. Asking a question, talking, "
    "looking around and walking somewhere safe are never checks: for those, reply with the single word NONE.]"
)
_NARRATE_OUTCOME = (
    "[The engine has decided: {outcomes}. Narrate exactly that result, and do not soften it. "
    f"Put {CHECK_MARKER} on its own line at the exact moment the result happens; the game prints the dice "
    "there. Write the prose now.]"
)
_OUTCOME_MEANINGS = {
    "triumph": "a triumph, better than hoped",
    "success": "a clean success",
    "success_at_cost": "success, but at a real and visible cost",
    "failure": "a failure: the attempt does not work and things get worse",
}
_SCRIBE_PROMPT = (
    "[Scribe step, no more story. Record only what this scene really did; most turns need just one or two "
    "calls. grant_xp if a check was passed or survived, if offered. apply_effect if the player was hurt (use "
    "a check_id or hazard:<name>). adjust_standing only if a named person or god who matters saw a deed. "
    "register_hook only for a new choice or person who should matter later. advance_time whenever the scene "
    "took real time, such as a journey or a sleep (rest also heals). send_petition if a sworn god asked a "
    "small thing; resolve_petition when one was done or refused. engage_clock if a tested deed touched a "
    "global clock's threads. Always finish with "
    "suggest_actions: 3 to 4 actions that fit this exact moment, one non-violent, one with a cost or risk in "
    "its cost field, no digits. Each label is one brief plain line. Give an uncertain action a check (stat, "
    "difficulty, challenge_tier, stakes); talking, asking and looking have none. A line only this character "
    "could choose gets a tag naming its Oath, class, profession or people, from the sheet.]"
)
_SCRIBE_TOOLS = (
    "grant_xp",
    "apply_effect",
    "adjust_standing",
    "register_hook",
    "set_flag",
    "advance_time",
    "send_petition",
    "resolve_petition",
    "engage_clock",
    "suggest_actions",
)
_SUGGEST_PROMPT = (
    "[Now call suggest_actions with 3 to 4 next actions for the player, each one brief plain line. Include a "
    "non-violent action and one with a visible cost or risk in its cost field. Give an uncertain action a "
    "check (stat, difficulty, challenge_tier, stakes); talking, asking and looking have none. A line only "
    "this character could choose gets a tag naming its Oath, class, profession or people, from the sheet. "
    "Use no digits. Write no more prose.]"
)


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
        self.outcomes: list[str] = []
        self.recent: list[str] = []
        # The template renders tools before the history, so a changing list empties the model's cache (D-031).
        self.tools = tool_definitions()

    def call(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None, *, fast: bool = False
    ) -> LLMReply:
        reply = self.client.complete(self.system, messages, tools, fast=fast)
        self.tokens = [
            self.tokens[0] + reply.tokens_in,
            self.tokens[1] + reply.tokens_cached,
            self.tokens[2] + reply.tokens_out,
        ]
        return reply

    def run_tools(self, reply: LLMReply, offered: set[str]) -> list[dict[str, Any]]:
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
                if call.name in offered:
                    result = apply_tool(self.sim, call.name, call.args)
                else:
                    result = ToolResult(call.name, False, reason=f"{call.name} is not available right now")
                payload = result.payload()
                if result.accepted:
                    self.allowed |= _numbers_in(result.data)
                    self.log.append(f"ok {call.name}")
                    if "outcome" in result.data:
                        self.outcomes.append(result.data["outcome"])
                else:
                    self.rejections[call.name] += 1
                    self.log.append(f"rejected {call.name}: {result.reason}")
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(payload)})
        return results

    def roll_chosen(self, messages: list[dict[str, Any]], check: dict[str, Any]) -> bool:
        """Roll the check the player saw on the option they picked (D-036). False if it no longer applies."""
        result = apply_tool(self.sim, "request_check", check)
        if not result.accepted:
            self.log.append(f"rejected chosen check: {result.reason}")
            return False
        self.allowed |= _numbers_in(result.data)
        self.outcomes.append(result.data["outcome"])
        note = _NARRATE_OUTCOME.format(outcomes=_OUTCOME_MEANINGS[result.data["outcome"]])
        messages[-1] = {**messages[-1], "content": f"{messages[-1]['content']}\n\n{note}"}
        return True

    def referee(self, messages: list[dict[str, Any]]) -> None:
        """Roll before any prose exists, so the story has to follow the dice (ENG-02, ENG-04)."""
        trial = [
            *messages[:-1],
            {"role": "user", "content": f"{messages[-1]['content']}\n\n{_REFEREE_PROMPT}"},
        ]
        for _ in range(self.max_retries + 1):
            reply = self.call(trial, self.tools, fast=True)
            if not reply.tool_calls:
                return
            results = self.run_tools(reply, {"request_check"})
            trial += [{"role": "assistant", "content": reply.blocks()}, {"role": "user", "content": results}]
            if self.outcomes:
                note = ", then ".join(_OUTCOME_MEANINGS[o] for o in self.outcomes)
                messages += [
                    {"role": "assistant", "content": reply.blocks()},
                    {
                        "role": "user",
                        "content": [
                            *results,
                            {"type": "text", "text": _NARRATE_OUTCOME.format(outcomes=note)},
                        ],
                    },
                ]
                return

    def narrate(self, messages: list[dict[str, Any]]) -> str | None:
        """Prose with no tools, checked before anyone sees it. None means use the fallback text (NAR-07)."""
        for _ in range(self.max_retries + 1):
            reply = self.call(messages, self.tools)
            text = strip_action_list(reply.text).strip()
            problems = ["the reply is empty"] if not text else prose_problems(text, self.allowed)
            if reply.tool_calls:
                problems.append("this step is prose only, with no tool calls")
            if repeats_earlier_turn(text, self.recent):
                problems.append(
                    "it repeats earlier narration; answer what the player just did with new events"
                )
            if not problems:
                return text
            self.log.append("rejected prose: " + "; ".join(problems))
            messages += [
                {"role": "assistant", "content": [{"type": "text", "text": text or "(no reply)"}]},
                {
                    "role": "user",
                    "content": "[That narration was not shown, because "
                    + "; ".join(problems)
                    + ". Write the whole narration again without that.]",
                },
            ]
        return None

    def scribe(
        self, messages: list[dict[str, Any]], narration: str, names: tuple[str, ...], rounds: int
    ) -> None:
        """Record consequences after the prose. If this fails, the prose still stands."""
        messages += [
            {"role": "assistant", "content": [{"type": "text", "text": narration}]},
            {"role": "user", "content": _SCRIBE_PROMPT if len(names) > 1 else _SUGGEST_PROMPT},
        ]
        for _ in range(rounds):
            reply = self.call(messages, self.tools, fast=True)
            if not reply.tool_calls:
                break
            messages += [
                {"role": "assistant", "content": reply.blocks()},
                {"role": "user", "content": self.run_tools(reply, set(names))},
            ]
            if self.sim.suggested:
                return
        if not self.sim.suggested and len(names) > 1:
            messages.append({"role": "user", "content": _SUGGEST_PROMPT})
            reply = self.call(messages, self.tools, fast=True)
            self.run_tools(reply, {"suggest_actions"})


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
    max_rounds: int = 3,
    max_retries: int = 2,
    violence: str = "moderate",
    chosen_check: dict[str, Any] | None = None,
) -> TurnOutcome:
    """Play one turn without touching storage. The caller commits the outcome atomically (OPS-03)."""
    rng = RngStreams.from_state(rng_state)
    sim = Simulation(state, rng, rules, turn)
    system, messages = assemble(state, world, recent, player_input, violence)
    run = _Turn(client, sim, max_retries, system)
    run.recent = [narration for _, narration in recent]
    run.allowed = _numbers_in(state_view(state))  # Prose may quote the engine's own sheet (D-033).
    narration: str | None = None
    try:
        # Until the player answers the Dual Offer the scene is only talk, so there is nothing to roll.
        rolled = chosen_check is not None and run.roll_chosen(messages, chosen_check)
        # Bracketed text is the game speaking.
        if not rolled and state.offer_resolved and not player_input.startswith("["):
            run.referee(messages)
        narration = run.narrate(messages)
        if narration is not None:
            narration = place_notices(narration, sim.events)
            names = _SCRIBE_TOOLS if state.offer_resolved else ("suggest_actions",)
            if not sim.checks:  # XP rewards a tested deed, so a talking turn cannot farm it.
                names = tuple(n for n in names if n != "grant_xp")
            run.scribe(messages, narration, names, max_rounds)
    except LLMUnavailable as exc:
        run.log.append(f"model unavailable: {exc}")
    if narration is not None and not sim.suggested:
        sim.emit("actions_suggested", {"actions": []})  # Old actions would no longer fit this scene.
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
