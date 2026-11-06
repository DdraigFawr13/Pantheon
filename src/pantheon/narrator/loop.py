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

from pantheon.engine.combat import downed_exchange
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

REFEREE_PROMPT = (
    "[Referee step, no story yet. If the player is attempting something physical, risky, stealthy, forceful "
    "or deceptive whose result is not certain, call request_check now and choose the stat, difficulty and "
    "challenge_tier. If the action names a stat in brackets, use that stat. Asking a question, talking, "
    "looking around and walking somewhere safe are never checks: for those, reply with the single word NONE.]"
)
FIGHT_REFEREE_PROMPT = (
    "[Referee step, no story yet. A fight is on, so unless the player is only talking, call fight_move now. "
    "move is attack (with target, a foe's id from the Due list), guard or flee; stat is the stat the action "
    "really uses; skill only if a skill on the sheet applies. Reply with the single word NONE only for pure "
    "talk, in which case no exchange happens.]"
)
DOWNED_NOTE = (
    "[The character is Downed and cannot act; what the player typed is only what they try. The engine has "
    "decided: {summary} Narrate exactly that.]"
)
NARRATE_OUTCOME = (
    "[The engine has decided: {outcomes}. Narrate exactly that result, and do not soften it. "
    f"Put {CHECK_MARKER} on its own line at the exact moment the result happens; the game prints the dice "
    "there. Write the prose now.]"
)
OUTCOME_MEANINGS = {
    "triumph": "a triumph, better than hoped",
    "success": "a clean success",
    "success_at_cost": "success, but at a real and visible cost",
    "failure": "a failure: the attempt does not work and things get worse",
}
SCRIBE_PROMPT = (
    "[Scribe step, no more story. Record only what this scene really did; most turns need just one or two "
    "calls. grant_xp if a check was passed or survived, if offered. apply_effect if the player was hurt (use "
    "a check_id or hazard:<name>). adjust_standing only if a named person or god who matters saw a deed. "
    "register_hook only for a new choice or person who should matter later. advance_time whenever the scene "
    "took real time, such as a journey or a sleep (rest also heals). send_petition if a sworn god asked a "
    "small thing; resolve_petition when one was done or refused. engage_clock if a tested deed touched a "
    "global clock's threads. start_fight when foes attack or the player attacks them, and end_fight only if "
    "the story ends one early; the engine sets all fight damage, and searches won fights itself. grant_loot "
    "when a passed check opened a stash (cache:<what>) or earned a bounty (bounty:<who>). adjust_inventory "
    "and adjust_currency when items or coin change hands in the story, at the economy list's prices; "
    "invent no item outside the item list. Always finish with "
    "suggest_actions: 3 to 4 actions that fit this exact moment, one non-violent, one with a cost or risk in "
    "its cost field, no digits. Each label is one brief plain line. Give an uncertain action a check (stat, "
    "difficulty, challenge_tier, stakes); talking, asking and looking have none. A line only this character "
    "could choose gets a tag naming its Oath, class, profession or people, from the sheet. During a fight, "
    "give each action a fight (move, target, stat) instead of a check.]"
)
SCRIBE_TOOLS = (
    "grant_xp",
    "apply_effect",
    "adjust_standing",
    "register_hook",
    "set_flag",
    "advance_time",
    "send_petition",
    "resolve_petition",
    "engage_clock",
    "grant_loot",
    "adjust_inventory",
    "adjust_currency",
    "start_fight",
    "end_fight",
    "suggest_actions",
)
SUGGEST_PROMPT = (
    "[Now call suggest_actions with 3 to 4 next actions for the player, each one brief plain line. Include a "
    "non-violent action and one with a visible cost or risk in its cost field. Give an uncertain action a "
    "check (stat, difficulty, challenge_tier, stakes); talking, asking and looking have none. A line only "
    "this character could choose gets a tag naming its Oath, class, profession or people, from the sheet. "
    "During a fight, give each action a fight (move, target, stat) instead of a check. Use no digits. Write "
    "no more prose.]"
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


def numbers_in(value: Any) -> set[int]:
    if isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {value}
    if isinstance(value, dict):
        return set().union(*(numbers_in(v) for v in value.values())) if value else set()
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
        self.details: list[str] = []  # What each exchange did, from the engine (D-039).
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
                    self.allowed |= numbers_in(result.data)
                    self.log.append(f"ok {call.name}")
                    if "outcome" in result.data:
                        self.outcomes.append(result.data["outcome"])
                        self.details += [result.data["summary"]] if "summary" in result.data else []
                else:
                    self.rejections[call.name] += 1
                    self.log.append(f"rejected {call.name}: {result.reason}")
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(payload)})
        return results

    def roll_chosen(self, messages: list[dict[str, Any]], check: dict[str, Any]) -> bool:
        """Roll the check the player saw on the option they picked (D-036). False if it no longer applies."""
        result = apply_tool(self.sim, "fight_move" if "move" in check else "request_check", check)
        if not result.accepted:
            self.log.append(f"rejected chosen check: {result.reason}")
            return False
        self.allowed |= numbers_in(result.data)
        self.outcomes.append(result.data["outcome"])
        note = NARRATE_OUTCOME.format(outcomes=OUTCOME_MEANINGS[result.data["outcome"]])
        summary = f" {result.data['summary']}" if "summary" in result.data else ""
        messages[-1] = {**messages[-1], "content": f"{messages[-1]['content']}\n\n{note}{summary}"}
        return True

    def downed(self, messages: list[dict[str, Any]]) -> None:
        """A hostile exchange runs whatever the player typed, since the Downed cannot act (D-039)."""
        data = downed_exchange(self.sim)
        self.allowed |= numbers_in(data)
        note = DOWNED_NOTE.format(summary=data["summary"])
        messages[-1] = {**messages[-1], "content": f"{messages[-1]['content']}\n\n{note}"}

    def referee(self, messages: list[dict[str, Any]]) -> None:
        """Roll before any prose exists, so the story has to follow the dice (ENG-02, ENG-04)."""
        in_fight = self.sim.state.fight is not None
        prompt = FIGHT_REFEREE_PROMPT if in_fight else REFEREE_PROMPT
        trial = [
            *messages[:-1],
            {"role": "user", "content": f"{messages[-1]['content']}\n\n{prompt}"},
        ]
        for _ in range(self.max_retries + 1):
            reply = self.call(trial, self.tools, fast=True)
            if not reply.tool_calls:
                return
            results = self.run_tools(reply, {"fight_move" if in_fight else "request_check"})
            trial += [{"role": "assistant", "content": reply.blocks()}, {"role": "user", "content": results}]
            if self.outcomes:
                note = ", then ".join(OUTCOME_MEANINGS[o] for o in self.outcomes)
                note = " ".join([note, *self.details])
                messages += [
                    {"role": "assistant", "content": reply.blocks()},
                    {
                        "role": "user",
                        "content": [
                            *results,
                            {"type": "text", "text": NARRATE_OUTCOME.format(outcomes=note)},
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
            {"role": "user", "content": SCRIBE_PROMPT if len(names) > 1 else SUGGEST_PROMPT},
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
            messages.append({"role": "user", "content": SUGGEST_PROMPT})
            reply = self.call(messages, self.tools, fast=True)
            self.run_tools(reply, {"suggest_actions"})


def turn_tools(
    state: GameState,
    player_input: str,
    *,
    rolled: bool = False,
    narrated: bool = False,
    checked: bool = False,
) -> tuple[str, ...]:
    """The tools a turn may use now: the one rule behind the API loop and `pantheon session` (D-031).

    Before the prose, only the referee's `request_check`, or `fight_move` in a fight (D-039); nothing while
    Downed in a fight, since the foes' exchange runs by itself. Until the player answers the Dual Offer the
    scene is only talk, so there is nothing to roll; bracketed text is the game speaking. After the prose, the
    scribe's tools. XP rewards a tested deed, so a turn with no check cannot grant it.
    """
    if not narrated:
        talk = player_input.startswith("[")
        if rolled or not state.offer_resolved or talk or (state.fight is not None and state.downed):
            return ()
        return ("fight_move",) if state.fight is not None else ("request_check",)
    names = SCRIBE_TOOLS if state.offer_resolved else ("suggest_actions",)
    return names if checked else tuple(n for n in names if n != "grant_xp")


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
    seed: int | None = None,
) -> TurnOutcome:
    """Play one turn without touching storage. The caller commits the outcome atomically (OPS-03)."""
    rng = RngStreams.from_state(rng_state, seed)
    sim = Simulation(state, rng, rules, turn)
    system, messages = assemble(state, world, recent, player_input, violence)
    run = _Turn(client, sim, max_retries, system)
    run.recent = [narration for _, narration in recent]
    run.allowed = numbers_in(state_view(state))  # Prose may quote the engine's own sheet (D-033).
    narration: str | None = None
    try:
        rolled = False
        if state.fight is not None and state.downed:
            run.downed(messages)
            rolled = True
        elif chosen_check is not None:
            rolled = run.roll_chosen(messages, chosen_check)
        if turn_tools(state, player_input, rolled=rolled):
            run.referee(messages)
        narration = run.narrate(messages)
        if narration is not None:
            narration = place_notices(narration, sim.events)
            names = turn_tools(state, player_input, narrated=True, checked=bool(sim.checks))
            if any(type_ == "reckoning" for type_, _ in sim.events):  # The dead earn nothing for dying.
                names = ("suggest_actions",)
            if not sim.state.dead:
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
