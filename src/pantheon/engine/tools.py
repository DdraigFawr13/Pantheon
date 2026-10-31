"""Narrator tools (ENG-02, architecture section 6). Each one validates, rolls, then emits events.

This is the thin slice's set (D-029). The narrator names a kind; the engine sets the size (ENG-09).
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pantheon.engine.calendar import (
    MINUTES_PER_DAY,
    REST_MINUTES,
    clock_value,
    counted_days,
    date_of,
    pass_time,
)
from pantheon.engine.checks import (
    Approach,
    CheckOdds,
    CheckRequest,
    Difficulty,
    Outcome,
    OvercomeClaim,
    OvercomeKind,
    check_odds,
    resolve_check,
)
from pantheon.engine.progression import evolution_options, offer_skills
from pantheon.engine.state import STATS, Action, GameState, xp_to_next
from pantheon.engine.timeline import Rejected, Simulation, change_standing
from pantheon.world.schemas import GameData

MAX_REJECTION_DETAIL = 3
MAX_STANDING_PER_TURN = 2
MAX_HOOKS_PER_TURN = 2
MAX_TIME_CALLS_PER_TURN = 2
_SPANS = {  # Minutes in one, and the most one call may ask for.
    "minutes": (1, 240),
    "hours": (60, 24),
    "rest": (REST_MINUTES, 1),
    "day": (MINUTES_PER_DAY, 1),
    "days": (MINUTES_PER_DAY, 90),
}
_FLAG_KEY = re.compile(r"^story\.[a-z][a-z0-9_.]*$")
_DIGIT = re.compile(r"\d")
_OATH_CHOICE = re.compile(r"\b(swear|accept|refuse)\b", re.I)
MAX_ACTION_WORDS = 12


@dataclass(frozen=True)
class ToolResult:
    name: str
    accepted: bool
    data: dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    def payload(self) -> dict[str, Any]:
        if self.accepted:
            return {"status": "accepted", **self.data}
        return {"status": "rejected", "reason": self.reason}


class _Args(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RequestCheck(_Args):
    """Roll a check when an action has an uncertain outcome and real stakes, before narrating the result."""

    stat: Literal["vigor", "agility", "intellect", "resolve", "presence"]
    difficulty: Difficulty
    challenge_tier: int = Field(ge=0, le=8, description="Tier of the opposition or obstacle, 0 to 8.")
    approach: Approach = Field(default=Approach.OTHER, description="force for direct force, else other.")
    skill: str | None = Field(default=None, description="A skill on the sheet that applies, if any.")
    stakes: str = Field(default="", description="What is at risk, in a few words.")
    overcome: Literal["oath", "terrain", "divine_favor"] | None = Field(
        default=None, description="An Overcome Condition, for direct force far above the character's tier."
    )


class ApplyEffect(_Args):
    """Damage or heal the player's character. The engine sets the size."""

    kind: Literal["damage", "heal"]
    source: str = Field(
        description="damage: a check_id this turn, or hazard:<name>. heal: aid:<name>, or rest after sleep."
    )
    reason: str


class GrantXp(_Args):
    """Award experience for a deed. Name the kind; the engine sets the amount."""

    kind: Literal["minor", "major", "milestone"]
    reason: str


class AdjustStanding(_Args):
    """Change Standing with a god, faction or person after a deed they would care about."""

    entity: str = Field(description="Lower-case id, such as a god's id.")
    kind: Literal["slight", "notable", "grave"]
    direction: Literal["+", "-"]
    witness: str = Field(
        default="none",
        description="Who saw it: npc:<name>, evidence:<item> or record:<office>; none if unseen.",
    )
    reason: str


class SetFlag(_Args):
    """Remember a story fact. The key must start with story. and the value is true or false."""

    key: str
    value: bool
    reason: str = ""


class RegisterHook(_Args):
    """Record a consequence that should come back later. Call it for every significant choice."""

    description: str
    due_condition: str = Field(description="When this should come due, in plain words.")
    source_choice: str = ""


class AdvanceTime(_Args):
    """Move the calendar when time really passes: a walk, a journey, a night's sleep. rest also heals."""

    span: Literal["minutes", "hours", "rest", "day", "days"]
    count: int = Field(default=1, ge=1, description="How many of that span; rest and day are always 1.")
    reason: str


class SendPetition(_Args):
    """A god the character is sworn to asks a small thing through a Vessel or an omen."""

    god: str = Field(description="Lower-case id of a god the character has sworn to.")
    ask: str = Field(description="The task, refusal or offering asked for, in a few words.")
    due_condition: str = Field(description="When it should be done, in plain words.")


class ResolvePetition(_Args):
    """Close an open petition after the player granted or refused it. Time lapses one left ignored."""

    hook_id: int
    granted: bool
    reason: str


class EngageClock(_Args):
    """Record that a tested deed this turn touched a global clock's threads, so it is not neglected."""

    clock_id: str = Field(description="seat_vote, rift_tide, grain_war, ember_fever or lanterns_price.")
    reason: str


class SuggestedAction(_Args):
    label: str = Field(description=f"One brief line of at most {MAX_ACTION_WORDS} words, with no digits.")
    violent: bool = False
    cost: str | None = Field(default=None, description="A visible cost or risk, in words with no digits.")
    tag: str | None = Field(
        default=None,
        description="An Oath, class, profession or people the character has, when this line is one only they "
        "could choose. A check shows its own stat or skill, so omit the tag for those.",
    )
    check: RequestCheck | None = Field(
        default=None,
        description="The check this action would roll, if it is uncertain; the game shows the odds and rolls "
        "exactly this when picked. Omit it for talking, asking and looking, which never roll.",
    )


class SuggestActions(_Args):
    """Offer 3 to 4 next actions, differing in kind: one non-violent, and one with a visible cost or risk."""

    actions: list[SuggestedAction]


def _check_request(state: GameState, data: GameData, args: RequestCheck) -> CheckRequest:
    overcome = None
    if args.overcome == "oath":
        if not state.oaths:
            raise Rejected("no Oath is sworn, so an Oath cannot be the Overcome Condition")
        overcome = OvercomeClaim(OvercomeKind.OATH)
    elif args.overcome == "terrain":
        overcome = OvercomeClaim(OvercomeKind.TERRAIN)
    elif args.overcome == "divine_favor":
        best = max((state.standing.get(g, 0) for g in data.god_ids()), default=0)
        overcome = OvercomeClaim(OvercomeKind.DIVINE_FAVOR, standing=best)
    return CheckRequest(
        difficulty=args.difficulty,
        stat=state.stats[args.stat],
        skill_rank=state.skills.get((args.skill or "").lower(), 0),
        actor_tier=state.tier,
        challenge_tier=args.challenge_tier,
        approach=args.approach,
        overcome=overcome,
    )


def check_preview(state: GameState, data: GameData, check: dict[str, Any]) -> CheckOdds:
    """The odds a stored action's check has right now, for the screen (D-036)."""
    return check_odds(_check_request(state, data, RequestCheck.model_validate(check)))


def _request_check(sim: Simulation, args: RequestCheck) -> dict[str, Any]:
    state = sim.state
    request = _check_request(state, sim.rules.data, args)
    skill_rank = request.skill_rank
    result = resolve_check(sim.rng, request)
    check_id = f"c{state.checks_made + 1}"
    sim.checks[check_id] = result.outcome
    event = {
        "check_id": check_id,
        "stat": args.stat,
        "stat_value": state.stats[args.stat],
        "skill": args.skill,
        "skill_rank": skill_rank,
        "difficulty": args.difficulty.value,
        "challenge_tier": args.challenge_tier,
        "approach": args.approach.value,
        "stakes": args.stakes,
        "tier_gap": result.tier_gap,
        "chance": result.chance,
        "roll": result.roll,
        "outcome": result.outcome.value,
        "complication": result.complication,
        "automatic": result.automatic,
        "overcome_applied": result.overcome_applied,
    }
    sim.emit("check_resolved", event)
    return {
        "check_id": check_id,
        "outcome": result.outcome.value,
        "complication": result.complication,
        "automatic": result.automatic,
    }


def _apply_effect(sim: Simulation, args: ApplyEffect) -> dict[str, Any]:
    state = sim.state
    table = sim.rules.data.rewards
    if args.kind == "damage":
        if state.downed:
            raise Rejected("the character is already Downed")
        if args.source in sim.checks:
            if args.source in sim.damaged_by:
                raise Rejected(f"{args.source} has already caused damage")
            percent = table.damage_percent.get(sim.checks[args.source].value)
            if percent is None:
                raise Rejected(f"{args.source} succeeded, so it causes no damage")
            sim.damaged_by.add(args.source)
        elif args.source.startswith("hazard:"):
            percent = table.damage_percent["hazard"]
        else:
            raise Rejected("source must be a check_id from this turn or hazard:<name>")
        amount = min(math.ceil(state.max_hp * percent / 100), state.hp)
    else:
        if state.wounds == 0 and not (args.source == "rest" and state.trial_recovery):
            raise Rejected("the character has no wounds to heal")
        if args.source == "rest":
            if sim.rested:
                raise Rejected("the character has already rested this turn")
            amount = state.wounds
            sim.rested = True
            pass_time(sim, REST_MINUTES, "rest", args.reason)
        elif args.source.startswith("aid:"):
            amount = min(math.ceil(state.max_hp * table.heal_percent["aid"] / 100), state.wounds)
        else:
            raise Rejected("source must be rest or aid:<name>")
    sim.emit(
        "effect_applied", {"kind": args.kind, "amount": amount, "source": args.source, "reason": args.reason}
    )
    if args.kind == "damage" and state.hp == 0:
        sim.emit("downed", {"reason": args.reason})
    return {"kind": args.kind, "hp": state.hp, "max_hp": state.max_hp, "downed": state.downed}


def _grant_xp(sim: Simulation, args: GrantXp) -> dict[str, Any]:
    state = sim.state
    table = sim.rules.data.rewards
    if state.level == 0:
        raise Rejected("the Unwritten have no level and gain no XP")
    amount = table.xp[args.kind]
    if sim.xp_this_turn + amount > table.xp_per_turn_cap:
        raise Rejected("this turn has reached its XP limit")
    sim.xp_this_turn += amount
    sim.emit("xp_gained", {"amount": amount, "kind": args.kind, "reason": args.reason})
    leveled = False
    while state.level % 10 != 0 and state.xp >= xp_to_next(state.level):
        _level_up(sim)
        leveled = True
    return {
        "kind": args.kind,
        "level": state.level,
        "leveled_up": leveled,
        "trial_required": state.trial_ready,
    }


def _level_up(sim: Simulation) -> None:
    state = sim.state
    table = sim.rules.data.rewards
    cls = sim.rules.data.class_of(state.class_id)
    gains = (
        {cls.primary: table.level_gains.primary, cls.secondary: table.level_gains.secondary} if cls else {}
    )
    sim.emit(
        "level_up",
        {
            "level": state.level + 1,
            "xp_spent": xp_to_next(state.level),
            "gains": gains,
            "free_points": table.level_gains.free_points,
        },
    )
    offer_skills(sim)


_TRIAL_RESULTS = {
    Outcome.TRIUMPH: "ascend",
    Outcome.SUCCESS: "ascend",
    Outcome.SUCCESS_AT_COST: "setback",
    Outcome.FAILURE: "breaking",
}
_INJURY_AMOUNT = 10


def attempt_trial(sim: Simulation) -> dict[str, Any]:
    """The Ascension Trial, a player's choice (D-037). Set at the next tier, on the class's primary stat."""
    state = sim.state
    if not state.trial_ready:
        raise Rejected("no Ascension Trial is due")
    if state.trial_recovery:
        raise Rejected("the character must recover before trying again")
    cls = sim.rules.data.class_of(state.class_id)
    if cls is None:
        raise Rejected("a character needs a class to attempt a Trial")
    checked = _request_check(
        sim,
        RequestCheck(
            stat=cls.primary,
            difficulty=Difficulty.ROUTINE,
            challenge_tier=state.tier + 1,
            stakes="the Ascension Trial",
        ),
    )
    result = _TRIAL_RESULTS[Outcome(checked["outcome"])]
    if result == "setback":
        sim.emit("xp_lost", {"amount": state.xp, "reason": "a Setback in the Ascension Trial"})
    elif result == "breaking":
        stat = sim.rng.choose_distinct("world", STATS, 1)[0]
        amount = min(_INJURY_AMOUNT, state.stats[stat])
        sim.emit(
            "injury_gained", {"stat": stat, "amount": amount, "reason": "a Breaking in the Ascension Trial"}
        )
    if result == "ascend":
        _level_up(sim)
    evolution_due = result == "ascend" and bool(evolution_options(state, sim.rules.data))
    sim.emit("trial_resolved", {"result": result, "evolution_due": evolution_due})
    return {"result": result, "level": state.level, "evolution_due": state.needs_evolution}


def _adjust_standing(sim: Simulation, args: AdjustStanding) -> dict[str, Any]:
    sim.count_call("adjust_standing", MAX_STANDING_PER_TURN)
    if args.witness == "none":
        sim.emit("rumour_recorded", {"text": f"{args.entity}: {args.reason}"})
        return {
            "rumour": True,
            "note": "No witness, so this spreads as a rumour and Standing does not change.",
        }
    delta = sim.rules.data.rewards.standing[args.kind] * (1 if args.direction == "+" else -1)
    change_standing(sim, args.entity, delta, args.reason)
    return {"entity": args.entity, "rumour": False}


def _advance_time(sim: Simulation, args: AdvanceTime) -> dict[str, Any]:
    state = sim.state
    minutes_each, most = _SPANS[args.span]
    if args.count > most:
        raise Rejected(f"at most {most} {args.span} in one call")
    if args.span == "rest" and sim.rested:
        raise Rejected("the character has already rested this turn")
    sim.count_call("advance_time", MAX_TIME_CALLS_PER_TURN)
    if args.span == "rest" and (state.wounds or state.trial_recovery):
        _apply_effect(sim, ApplyEffect(kind="heal", source="rest", reason=args.reason))
    else:
        sim.rested = sim.rested or args.span == "rest"
        pass_time(sim, minutes_each * args.count, args.span, args.reason)
    date = date_of(state.day)
    return {"date": date.view()}


def _send_petition(sim: Simulation, args: SendPetition) -> dict[str, Any]:
    state, data = sim.state, sim.rules.data
    gods = {o.god for o in data.oaths if o.id in state.oaths}
    if args.god not in gods:
        raise Rejected(f"{args.god} has no Oath from this character, so it sends no petitions")
    if any(h.petition_god == args.god and not h.resolved for h in state.hooks):
        raise Rejected(f"{args.god} already has an open petition")
    name = next(g.name for g in data.gods if g.id == args.god)
    return {
        "hook_id": _add_hook(
            sim,
            f"{name} asks: {args.ask}",
            args.due_condition,
            f"petition from {name}",
            petition_god=args.god,
            deadline_day=state.day + data.rewards.petition.days,
        )
    }


def _resolve_petition(sim: Simulation, args: ResolvePetition) -> dict[str, Any]:
    state = sim.state
    hook = next((h for h in state.hooks if h.id == args.hook_id and h.petition_god), None)
    if hook is None or hook.petition_god is None:
        raise Rejected(f"hook {args.hook_id} is not a petition")
    if hook.resolved:
        raise Rejected(f"petition {args.hook_id} is already closed")
    if hook.turn == sim.turn:
        raise Rejected("a petition cannot be closed in the turn it arrives")
    sim.count_call("adjust_standing", MAX_STANDING_PER_TURN)
    terms = sim.rules.data.rewards.petition
    sim.emit("petition_resolved", {"hook_id": hook.id, "granted": args.granted, "reason": args.reason})
    change_standing(sim, hook.petition_god, terms.granted if args.granted else -terms.ignored, args.reason)
    return {"hook_id": hook.id, "granted": args.granted}


def _engage_clock(sim: Simulation, args: EngageClock) -> dict[str, Any]:
    state, data = sim.state, sim.rules.data
    if not sim.checks:
        raise Rejected("only a tested deed this turn can touch a clock's threads")
    clock = next((c for c in data.clocks if c.id == args.clock_id), None)
    if clock is None:
        raise Rejected(f"there is no clock {args.clock_id}")
    if clock_value(state, data, clock.id) >= clock.segments:
        raise Rejected(f"{clock.name} is already filled")
    today = counted_days(state.day)
    if state.clocks_engaged.get(clock.id) == today:
        raise Rejected(f"{clock.name} has already been touched today")
    sim.emit("clock_engaged", {"clock": clock.id, "counted_day": today, "reason": args.reason})
    return {"clock": clock.id}


def _set_flag(sim: Simulation, args: SetFlag) -> dict[str, Any]:
    if args.key in sim.rules.flag_setters:
        raise Rejected(f"{args.key} cannot be set by the narrator in this build")
    if not _FLAG_KEY.match(args.key):
        raise Rejected("a narrator flag must start with story. and use lower-case letters")
    sim.emit("flag_set", {"key": args.key, "value": args.value, "reason": args.reason})
    return {"key": args.key, "value": args.value}


def _register_hook(sim: Simulation, args: RegisterHook) -> dict[str, Any]:
    return {"hook_id": _add_hook(sim, args.description, args.due_condition, args.source_choice)}


def _add_hook(
    sim: Simulation, description: str, due_condition: str, source_choice: str, **petition: Any
) -> int:
    if any(h.description == description for h in sim.state.hooks):
        raise Rejected("that hook is already registered")
    sim.count_call("register_hook", MAX_HOOKS_PER_TURN)
    hook_id = len(sim.state.hooks) + 1
    sim.emit(
        "hook_registered",
        {
            "id": hook_id,
            "turn": sim.turn,
            "description": description,
            "due_condition": due_condition,
            "source_choice": source_choice,
            **petition,
        },
    )
    return hook_id


def _character_tags(sim: Simulation) -> set[str]:
    """What a suggested action may be tagged with: only what this character really has (D-033)."""
    state, data = sim.state, sim.rules.data
    names = [*_rolled_tags(state), state.profession or ""]
    names += [o.name for o in data.oaths if o.id in state.oaths]
    current = data.class_of(state.class_id)
    names += [current.name] if current else []
    names += [p.name for p in data.peoples if p.id == state.people]
    return {name.lower() for name in names if name}


def _rolled_tags(state: GameState) -> set[str]:
    """Tags that promise a roll, so they must come with a check (D-036)."""
    return {*STATS, *state.skills}


def _settled_action(action: SuggestedAction, state: GameState, tags: set[str]) -> Action:
    tag = action.tag
    if tag is not None and tag.lower() not in tags:
        raise Rejected(f"this character has no {tag!r} to tag an action with")
    rolled = tag is not None and tag.lower() in _rolled_tags(state)
    if not state.offer_resolved:  # Nothing rolls before the Dual Offer is answered.
        return Action(
            label=action.label, violent=action.violent, cost=action.cost, tag=None if rolled else tag
        )
    if rolled and action.check is None:
        raise Rejected(f"the tag {tag!r} promises a roll, so give that action a check")
    if action.check is not None and tag is None:
        tag = action.check.skill or action.check.stat
    return Action(**{**action.model_dump(mode="json"), "tag": tag})


def _suggest_actions(sim: Simulation, args: SuggestActions) -> dict[str, Any]:
    actions = args.actions
    minimum = 3
    if not sim.state.offer_resolved:  # The game's menu already offers swearing and refusing.
        actions = [a for a in actions if not _OATH_CHOICE.search(a.label)]
        minimum = 1
    if not minimum <= len(actions) <= 4:
        raise Rejected("offer 3 to 4 actions")
    if any(len(a.label.split()) > MAX_ACTION_WORDS for a in actions):
        raise Rejected(f"keep each action to {MAX_ACTION_WORDS} words")
    tags = _character_tags(sim)
    settled = [_settled_action(a, sim.state, tags) for a in actions]
    for action in settled:
        if action.check is not None:
            check_preview(sim.state, sim.rules.data, action.check)
    if all(a.violent for a in actions):
        raise Rejected("at least one action must be non-violent")
    if not any(a.cost for a in args.actions):
        raise Rejected("at least one action must name a visible cost or risk in its cost field")
    if any(_DIGIT.search(a.label + (a.cost or "")) for a in actions):
        raise Rejected("action labels and costs must not contain digits; the engine owns the numbers")
    sim.emit("actions_suggested", {"actions": [a.model_dump() for a in settled]})
    sim.suggested = True
    return {"count": len(actions)}


def resolve_offer(sim: Simulation, choice: str) -> dict[str, Any]:
    """Settle the opening's Dual Offer (world/protagonist_seed.md). A player command, not a narrator tool."""
    state = sim.state
    data = sim.rules.data
    if state.offer_resolved:
        raise Rejected("the Dual Offer has already been resolved")
    choice = choice.strip().lower().replace("-", "_")
    gods = {g.id: g for g in data.gods if g.id in state.opening_gods}
    oaths = {o.id: o for o in data.oaths}
    if choice != "refuse" and choice not in gods:
        raise Rejected(f"choice must be refuse or one of {sorted(gods)}")
    ordered = sorted(gods)
    if choice == "refuse":
        rival_god = ordered[sim.rng.roll("rival", 2) - 1]
        sim.emit("flag_set", {"key": "unwritten_path", "value": True, "reason": "refused both Oaths"})
        result: dict[str, Any] = {"sworn": None, "level": 0}
    else:
        oath = oaths[gods[choice].first_oath]
        rank = min(state.affinities.get(oath.affinity, 0) + 1, 2)
        sim.emit(
            "oath_sworn",
            {"oath": oath.id, "god": choice, "affinity": oath.affinity, "affinity_rank": rank, "level": 1},
        )
        rival_god = next(g for g in ordered if g != choice)
        result = {"sworn": oath.id, "level": 1, "affinity": oath.affinity, "affinity_rank": rank}
    sim.emit("flag_set", {"key": "opening.dual_offer_resolved", "value": True, "reason": "the Dual Offer"})
    rival_oath = oaths[gods[rival_god].first_oath]
    sim.exempt_from_limits = True
    for god_id in ordered:
        name = gods[god_id].name
        verb = "answer to the Oath" if god_id == choice else "response to being refused"
        _register_hook(
            sim,
            RegisterHook(
                description=f"{name}'s {verb}",
                due_condition="within the next few days, through a Vessel or an omen",
                source_choice=f"Dual Offer: {choice}",
            ),
        )
    _register_hook(
        sim,
        RegisterHook(
            description=f"A rival who survived the fall swore {rival_oath.name} to {gods[rival_god].name}",
            due_condition="when the player next deals with Rifters or that god's people",
            source_choice=f"Dual Offer: {choice}",
        ),
    )
    sim.exempt_from_limits = False
    return result


_TOOLS: dict[str, tuple[type[_Args], Callable[[Simulation, Any], dict[str, Any]]]] = {
    "request_check": (RequestCheck, _request_check),
    "apply_effect": (ApplyEffect, _apply_effect),
    "grant_xp": (GrantXp, _grant_xp),
    "adjust_standing": (AdjustStanding, _adjust_standing),
    "set_flag": (SetFlag, _set_flag),
    "register_hook": (RegisterHook, _register_hook),
    "advance_time": (AdvanceTime, _advance_time),
    "send_petition": (SendPetition, _send_petition),
    "resolve_petition": (ResolvePetition, _resolve_petition),
    "engage_clock": (EngageClock, _engage_clock),
    "suggest_actions": (SuggestActions, _suggest_actions),
}


def apply_tool(sim: Simulation, name: str, args: dict[str, Any]) -> ToolResult:
    """Validate and apply one narrator call. An invalid call changes nothing (ENG-02)."""
    if name not in _TOOLS:
        return ToolResult(name, False, reason=f"unknown tool {name}; use only the tools listed")
    schema, handler = _TOOLS[name]
    try:
        parsed = schema.model_validate(args)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:MAX_REJECTION_DETAIL]
        )
        return ToolResult(name, False, reason=details)
    try:
        return ToolResult(name, True, handler(sim, parsed))
    except Rejected as exc:
        return ToolResult(name, False, reason=str(exc))


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            return _inline_refs(defs[node["$ref"].rsplit("/", 1)[-1]], defs)
        return {k: _inline_refs(v, defs) for k, v in node.items() if k != "$defs"}
    if isinstance(node, list):
        return [_inline_refs(v, defs) for v in node]
    return node


def tool_definition(name: str) -> dict[str, Any]:
    schema = _TOOLS[name][0]
    raw = schema.model_json_schema()
    return {
        "name": name,
        "description": (schema.__doc__ or "").strip(),
        "input_schema": _inline_refs(
            {k: v for k, v in raw.items() if k != "description"}, raw.get("$defs", {})
        ),
    }


def tool_definitions() -> list[dict[str, Any]]:
    return [tool_definition(name) for name in _TOOLS]
