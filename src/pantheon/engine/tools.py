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
from pantheon.engine.combat import injure, move_terms, resolve_exchange, start_fight
from pantheon.engine.loot import foes_down_xp, format_cp, roll_loot, scaled
from pantheon.engine.progression import evolution_options, gain_xp, level_up
from pantheon.engine.state import STATS, Action, GameState
from pantheon.engine.timeline import Rejected, Simulation, change_standing
from pantheon.engine.traits import bonuses, defence_stat, skill_cost, skill_data, trait_of
from pantheon.world.schemas import GameData, Item

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


class FoeArg(_Args):
    name: str
    tier: int = Field(ge=0, le=8)
    threat: str = Field(description="minion, standard or elite.")


class StartFight(_Args):
    """Foes attack, or the player attacks them: a fight begins. The engine shows what each foe intends."""

    foes: list[FoeArg]
    reason: str
    ambush: bool = Field(default=False, description="True if the character strikes first, unseen.")


class EndFight(_Args):
    """End a fight for a story reason, such as a surrender or foes breaking off. Never for the Downed."""

    reason: str


class FightMove(_Args):
    """The player's move in this exchange of a fight. The engine sets the difficulty and rolls."""

    move: Literal["attack", "guard", "flee", "item"]
    stat: Literal["vigor", "agility", "intellect", "resolve", "presence"]
    target: str | None = Field(default=None, description="For attack: the foe's id, such as f1.")
    skill: str | None = Field(default=None, description="A skill on the sheet that the move uses.")
    overspend: bool = Field(default=False, description="True if the player chose to spend below zero.")
    trait: bool = Field(default=False, description="True to call on the class's once-per-fight trait now.")
    pay_with_hp: bool = Field(default=False, description="Surge only: pay the skill's mana cost in HP.")
    item: str | None = Field(default=None, description="For item: a consumable the character carries.")


class GrantLoot(_Args):
    """After a tested deed pays off: a stash searched or a bounty paid. The engine rolls what it holds."""

    source: str = Field(
        pattern=r"^(cache|bounty):[A-Za-z0-9_ '-]{1,40}$",
        description="cache:<what was searched>, or bounty:<who paid it>.",
    )
    affinity: str | None = Field(default=None, description="A basic affinity the place leans to, if any.")
    reason: str


class AdjustInventory(_Args):
    """An item changes hands in the story: bought, given, found lying in plain sight, sold or lost."""

    item: str = Field(description="An item id from the game's item list.")
    quantity: int = Field(description="Plus to gain, minus to lose; never zero.")
    reason: str


class AdjustCurrency(_Args):
    """Coin changes hands in the story: a price paid, wages, a sale. Prices follow the economy list."""

    amount_cp: int = Field(description="Copper, plus to gain or minus to pay; 12 cp is 1 sp, 240 cp is 1 gp.")
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
    fight: FightMove | None = Field(default=None, description="During a fight: the move this action makes.")


class SuggestActions(_Args):
    """Offer 3 to 4 next actions, differing in kind: one non-violent, and one with a visible cost or risk."""

    actions: list[SuggestedAction]


def _check_request(
    state: GameState,
    data: GameData,
    args: RequestCheck,
    move: str | None = None,
    target: str | None = None,
    activating: bool = False,
) -> CheckRequest:
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
        bonus=sum(n for _, n in bonuses(state, data, args.stat, args.skill, move, target, activating)),
    )


def check_preview(state: GameState, data: GameData, check: dict[str, Any]) -> CheckOdds:
    """The odds a stored action's check has right now, for the screen (D-036)."""
    if "move" in check:
        move = FightMove.model_validate(check)
        request = _fight_terms(state, data, move)
        activating = move.trait and state.fight is not None and not state.fight.trait_used
        return check_odds(_check_request(state, data, request, move.move, move.target, activating))
    return check_odds(_check_request(state, data, RequestCheck.model_validate(check)))


def _request_check(sim: Simulation, args: RequestCheck) -> dict[str, Any]:
    if sim.state.fight is not None:
        raise Rejected("in a fight, the player's action is a fight_move")
    return _roll_check(sim, args)


def _roll_check(
    sim: Simulation, args: RequestCheck, move: str | None = None, target: str | None = None
) -> dict[str, Any]:
    state = sim.state
    request = _check_request(state, sim.rules.data, args, move, target)
    found = bonuses(state, sim.rules.data, args.stat, args.skill, move, target)
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
    if found:
        event["bonuses"] = [[name, amount] for name, amount in found]  # Shown on the Ledger line (D-045).
    sim.emit("check_resolved", event)
    return {
        "check_id": check_id,
        "outcome": result.outcome.value,
        "complication": result.complication,
        "automatic": result.automatic,
    }


def _rest_helps(state: GameState) -> bool:
    return bool(
        state.wounds or state.trial_recovery or state.mana_spent or state.stamina_spent or state.cooldowns
    )


def _apply_effect(sim: Simulation, args: ApplyEffect) -> dict[str, Any]:
    state = sim.state
    table = sim.rules.data.rewards
    if state.fight is not None and (args.kind == "damage" or args.source == "rest"):
        raise Rejected("in a fight, the exchange sets the damage, and nobody rests")
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
        if state.wounds == 0 and not (args.source == "rest" and _rest_helps(state)):
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
    amount = scaled(table.xp[args.kind], state, sim.rules.data)  # Larger at higher tiers (D-014, D-047).
    if sim.xp_this_turn + amount > table.xp_per_turn_cap:
        raise Rejected("this turn has reached its XP limit")
    sim.xp_this_turn += amount
    leveled = gain_xp(sim, amount, args.kind, args.reason)
    return {
        "kind": args.kind,
        "level": state.level,
        "leveled_up": leveled,
        "trial_required": state.trial_ready,
    }


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
    if state.fight is not None:
        raise Rejected("a Trial cannot start in a fight")
    if not state.trial_ready:
        raise Rejected("no Ascension Trial is due")
    if state.trial_recovery:
        raise Rejected("the character must recover before trying again")
    cls = sim.rules.data.class_of(state.class_id)
    if cls is None:
        raise Rejected("a character needs a class to attempt a Trial")
    checked = _roll_check(
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
        level_up(sim)
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
    if state.fight is not None and args.span != "minutes":
        raise Rejected("a fight takes minutes; end it first")
    if args.count > most:
        raise Rejected(f"at most {most} {args.span} in one call")
    if args.span == "rest" and sim.rested:
        raise Rejected("the character has already rested this turn")
    sim.count_call("advance_time", MAX_TIME_CALLS_PER_TURN)
    if args.span == "rest" and _rest_helps(state):
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


def _start_fight(sim: Simulation, args: StartFight) -> dict[str, Any]:
    return start_fight(sim, [(f.name, f.tier, f.threat) for f in args.foes], args.ambush)


def _end_fight(sim: Simulation, args: EndFight) -> dict[str, Any]:
    if sim.state.fight is None:
        raise Rejected("there is no fight to end")
    if sim.state.downed:
        raise Rejected("the Downed cannot be saved this way; aid them or let the exchanges run")
    foes_down_xp(sim)
    sim.emit("fight_ended", {"result": "story", "reason": args.reason})
    return {"fight_over": True}


def _fight_terms(state: GameState, data: GameData, args: FightMove) -> RequestCheck:
    """Validate a move and work out its check, from state alone, so the odds and the roll agree (GAME-02)."""
    fight = state.fight
    if fight is None:
        raise Rejected("there is no fight")
    if state.downed:
        raise Rejected("the Downed cannot act")
    if args.move == "item":
        raise Rejected("using an item does not roll")
    difficulty, tier = move_terms(state, data, args.move, args.target)
    trait = trait_of(state, data)
    if args.trait:
        kind = trait.once_per_fight if trait else None
        if kind is None:
            raise Rejected("this class has no trait to call on in a fight")
        if fight.trait_used:
            raise Rejected(f"{trait.name if trait else 'the trait'} is spent for this fight")
        if kind == "curse" and args.move != "attack":
            raise Rejected("a curse lands with an attack on its target")
    if args.skill is not None:
        forming = args.trait and trait is not None and trait.once_per_fight == "form"
        if trait is not None and trait.form_blocks_skills and (fight.form or forming):
            raise Rejected(f"no skills while {trait.name} lasts")
        _skill_cost(state, data, args)
    return RequestCheck(
        stat=defence_stat(state, data, args.stat, args.move),  # type: ignore[arg-type]
        difficulty=Difficulty(difficulty),
        challenge_tier=tier,
        approach=Approach.FORCE if args.move == "attack" else Approach.OTHER,
        skill=args.skill,
        stakes=f"{args.move} in the fight",
    )


def _skill_cost(state: GameState, data: GameData, args: FightMove) -> tuple[str | None, int, int]:
    """(pool, cost, overspent percent) of the move's skill, or Rejected if it cannot be used now.

    The pool is "hp" when Surge pays a mana cost in HP (D-045).
    """
    name = (args.skill or "").lower()
    if name not in state.skills:
        raise Rejected(f"{args.skill} is not on the sheet")
    if state.cooldowns.get(name):
        raise Rejected(f"{args.skill} is cooling down")
    skill = skill_data(data, name)
    if skill is None or skill.pool is None:
        return None, 0, 0  # A skill with no data, such as an origin's, costs nothing yet.
    cost = skill_cost(state, data, skill)
    if args.pay_with_hp:
        trait = trait_of(state, data)
        if trait is None or not trait.hp_for_mana or skill.pool != "mana":
            raise Rejected("only a Surge can pay a mana cost in HP")
        if state.hp <= cost:
            raise Rejected(f"paying {cost} HP would drop the character")
        return "hp", cost, 0
    current, maximum = (
        (state.mana, state.max_mana) if skill.pool == "mana" else (state.stamina, state.max_stamina)
    )
    after = current - cost
    if after >= 0:
        return skill.pool, cost, 0
    if not args.overspend:
        raise Rejected(
            f"{args.skill} costs more {skill.pool} than is left; the player must choose to overspend"
        )
    percent = math.ceil(-after * 100 / maximum) if maximum else 100
    if percent > data.combat.overspend_limit_percent:
        raise Rejected(f"{args.skill} would overspend past the limit")
    return skill.pool, cost, percent


def _spend_skill(sim: Simulation, args: FightMove) -> None:
    pool, cost, overspent = _skill_cost(sim.state, sim.rules.data, args)
    name = (args.skill or "").lower()
    skill = skill_data(sim.rules.data, name)
    # A cooldown of N shuts out the next N exchanges, and this exchange's own end also ticks it.
    cooldown = skill.cooldown + 1 if skill and skill.cooldown else 0
    if pool == "hp":
        sim.emit("effect_applied", {"kind": "damage", "amount": cost, "source": "surge", "reason": name})
        pool, cost = None, 0
    sim.emit("skill_spent", {"skill": name, "pool": pool, "cost": cost, "cooldown": cooldown})
    if overspent:
        chance = overspent * sim.rules.data.combat.injury_chance_per_percent
        roll = sim.rng.roll("combat", 100)
        sim.emit("overspend_rolled", {"skill": name, "percent": overspent, "chance": chance, "roll": roll})
        if roll <= chance:
            injure(sim, f"overspending {name}")


def _fight_move(sim: Simulation, args: FightMove) -> dict[str, Any]:
    state = sim.state
    if args.move == "item":
        return _fight_item(sim, args)
    request = _fight_terms(state, sim.rules.data, args)
    trait = trait_of(state, sim.rules.data)
    if args.trait and trait is not None and state.fight is not None:
        kind = trait.once_per_fight
        sim.emit(
            "trait_used", {"trait": trait.name, "kind": kind, "foe": args.target if kind == "curse" else None}
        )
    if args.skill is not None:
        _spend_skill(sim, args)
    checked = _roll_check(sim, request, args.move, args.target)
    outcome = Outcome(checked["outcome"])
    return {
        "check_id": checked["check_id"],
        "outcome": outcome.value,
        **resolve_exchange(sim, args.move, args.target, outcome),
    }


def _fight_item(sim: Simulation, args: FightMove) -> dict[str, Any]:
    """Using a consumable is the player's whole exchange: nothing rolls, and the foes' blows land."""
    state = sim.state
    if state.fight is None:
        raise Rejected("there is no fight")
    if state.downed:
        raise Rejected("the Downed cannot act")
    item = _held_consumable(state, sim.rules.data, args.item)
    use_consumable(sim, item)
    return {"item": item.id, **resolve_exchange(sim, "item", None, None)}


def _held_consumable(state: GameState, data: GameData, item_id: str | None) -> Item:
    item = data.item_of(item_id or "")
    if item is None or not state.inventory.get(item.id):
        raise Rejected(f"the character carries no {item_id}")
    if item.kind != "consumable":
        raise Rejected(f"{item.name} is not something to use up")
    if item.heal_percent and state.wounds == 0:
        raise Rejected("the character has no wounds to heal")
    return item


def use_consumable(sim: Simulation, item: Item) -> None:
    state = sim.state
    sim.emit("item_changed", {"item": item.id, "quantity": -1, "reason": "used"})
    if item.heal_percent:
        amount = min(math.ceil(state.max_hp * item.heal_percent / 100), state.wounds)
        sim.emit(
            "effect_applied",
            {"kind": "heal", "amount": amount, "source": f"item:{item.id}", "reason": item.name},
        )


def use_item(sim: Simulation, item_id: str) -> None:
    """A player command: use a consumable outside a fight (inside one it is the exchange's move)."""
    if sim.state.fight is not None:
        raise Rejected("in a fight, using an item is the move for the exchange")
    use_consumable(sim, _held_consumable(sim.state, sim.rules.data, item_id))


def equip_item(sim: Simulation, item_id: str) -> None:
    """A player command: wield a weapon or wear armour the character carries."""
    state = sim.state
    item = sim.rules.data.item_of(item_id)
    if item is None or not state.inventory.get(item.id):
        raise Rejected(f"the character carries no {item_id}")
    if not item.equippable:
        raise Rejected(f"{item.name} cannot be worn or wielded")
    if state.fight is not None:
        raise Rejected("there is no time to change gear in a fight")
    if state.equipped.get(item.kind) == item.id:
        raise Rejected(f"{item.name} is already in use")
    sim.emit("item_equipped", {"slot": item.kind, "item": item.id})


def unequip_item(sim: Simulation, slot: str) -> None:
    if slot not in sim.state.equipped:
        raise Rejected(f"nothing is in the {slot} slot")
    if sim.state.fight is not None:
        raise Rejected("there is no time to change gear in a fight")
    sim.emit("item_unequipped", {"slot": slot})


def _grant_loot(sim: Simulation, args: GrantLoot) -> dict[str, Any]:
    state = sim.state
    if state.fight is not None:
        raise Rejected("fallen foes are searched when the fight is won; the engine does it")
    if not any(o is not Outcome.FAILURE for o in sim.checks.values()):
        raise Rejected("loot follows a tested deed that paid off: roll a check first")
    table = args.source.split(":")[0]
    if table not in sim.rules.data.rewards.loot:
        raise Rejected(f"there is no {table} loot yet")
    if args.affinity is not None and args.affinity not in sim.rules.data.affinities.basic:
        raise Rejected(f"affinity must be a basic affinity, not {args.affinity}")
    sim.count_call("grant_loot", 1)  # Counted only once every check has passed (D-022).
    return roll_loot(sim, table, args.source, args.affinity)


def _adjust_inventory(sim: Simulation, args: AdjustInventory) -> dict[str, Any]:
    state, data = sim.state, sim.rules.data
    item = data.item_of(args.item)
    if item is None:
        raise Rejected(f"unknown item {args.item}; use an id from the item list")
    if args.quantity == 0:
        raise Rejected("quantity must not be zero")
    if args.quantity < 0 and state.inventory.get(item.id, 0) < -args.quantity:
        raise Rejected(f"the character does not carry {-args.quantity} {item.name}")
    if args.quantity > 0:
        if item.tier > max(1, state.tier) or item.rarity not in ("common", "uncommon"):
            raise Rejected(f"{item.name} is beyond what the story can simply hand over; it must be looted")
        added = sim.call_counts["items_added"] + args.quantity
        if added > data.rewards.items_per_turn and not sim.exempt_from_limits:
            raise Rejected(f"at most {data.rewards.items_per_turn} items arrive in one turn")
        sim.call_counts["items_added"] = added
    sim.emit("item_changed", {"item": item.id, "quantity": args.quantity, "reason": args.reason})
    return {"item": item.id, "carried": state.inventory.get(item.id, 0)}


def _adjust_currency(sim: Simulation, args: AdjustCurrency) -> dict[str, Any]:
    state, data = sim.state, sim.rules.data
    if args.amount_cp == 0:
        raise Rejected("amount_cp must not be zero")
    if args.amount_cp < 0 and state.purse_cp < -args.amount_cp:
        raise Rejected(f"the character has only {format_cp(state.purse_cp)}")
    if args.amount_cp > 0:
        bound = scaled(data.rewards.coin_gain_cp_per_turn, state, data)
        gained = sim.call_counts["coin_gained"] + args.amount_cp
        if gained > bound and not sim.exempt_from_limits:
            raise Rejected(f"at most {format_cp(bound)} comes in one turn at this tier; larger sums are loot")
        sim.call_counts["coin_gained"] = gained
    sim.emit("currency_changed", {"delta_cp": args.amount_cp, "reason": args.reason})
    return {"purse": format_cp(state.purse_cp)}


def _fight_check_dict(sim: Simulation, args: FightMove) -> dict[str, Any]:
    """What a suggested move stores: the check it will roll, for the odds, plus the move itself (D-036)."""
    request = _fight_terms(sim.state, sim.rules.data, args)
    return {**args.model_dump(mode="json"), **request.model_dump(mode="json")}


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


def _settled_action(
    action: SuggestedAction, state: GameState, tags: set[str], fight_check: dict[str, Any] | None = None
) -> Action:
    if fight_check is not None:
        tag = fight_check["skill"] or fight_check["stat"]
        return Action(
            label=action.label, violent=action.violent, cost=action.cost, tag=tag, check=fight_check
        )
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
    settled = []
    for suggested in actions:
        # The Downed cannot move, so what they would try stays words; the exchange runs regardless.
        moves = suggested.fight is not None and not sim.state.downed and suggested.fight.move != "item"
        fight_check = _fight_check_dict(sim, suggested.fight) if moves and suggested.fight else None
        base = suggested.model_copy(update={"fight": None})
        settled.append(_settled_action(base, sim.state, tags, fight_check))
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
    "start_fight": (StartFight, _start_fight),
    "end_fight": (EndFight, _end_fight),
    "fight_move": (FightMove, _fight_move),
    "grant_loot": (GrantLoot, _grant_loot),
    "adjust_inventory": (AdjustInventory, _adjust_inventory),
    "adjust_currency": (AdjustCurrency, _adjust_currency),
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
