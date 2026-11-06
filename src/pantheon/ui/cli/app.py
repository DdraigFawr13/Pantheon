"""`pantheon` command line: `new` creates a timeline, `play` runs the game, `fork` branches from a turn."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel

from pantheon.config import Config, load_config
from pantheon.engine.calendar import date_of, format_date
from pantheon.engine.checks import Approach, CheckRequest, Difficulty, check_odds, resolve_check
from pantheon.engine.combat import intent_label
from pantheon.engine.commands import (
    CharacterChoices,
    allocate_point,
    choose_attunement,
    choose_class,
    choose_profession,
    create_character,
    innate_affinity_options,
)
from pantheon.engine.loot import format_cp
from pantheon.engine.opening import draw_opening_gods
from pantheon.engine.preview import chance, preview_text
from pantheon.engine.progression import choose_evolution, evolution_options, pick_skill
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import STATS, Action, EventRecord, GameState, xp_to_next
from pantheon.engine.timeline import Rejected, Rules, Simulation
from pantheon.engine.tools import attempt_trial, equip_item, resolve_offer, unequip_item, use_item
from pantheon.engine.traits import needs_attunement, trait_of
from pantheon.llm.anthropic_adapter import AnthropicClient
from pantheon.llm.client import LLMClient
from pantheon.narrator.assemble import history_window
from pantheon.narrator.loop import TurnOutcome, take_turn
from pantheon.narrator.notices import check_notice
from pantheon.storage.db import Database, SaveError, TurnRecord
from pantheon.world.loader import World, load_world

type Ask = Callable[[str], str]

OPENING_INPUT = (
    "[The game begins. Open with The Dual Offer. Narrate the collapse of the Stair as it happens and the "
    "fall into the dark. Then each of the two gods speaks to the character directly, with a big personality "
    "in its own distinct voice, hinting at its Oath's gift and Burden without spelling them out; the game's "
    "menu states the terms. End with both voices waiting for an answer.]"
)
_REFUSE_TERMS = "No class or level. You grow through shards, gear, allies and reputation."
_BAR_WIDTH = 10
_COMMANDS = "[dim]Commands: sheet · hooks · use/equip/unequip <item> · help · quit[/dim]"
_FIGHT_COMMANDS = "[dim]Commands: inspect 2 · sheet · hooks · help · quit[/dim]"
_BARE_COMMANDS = {
    "sheet": "/sheet",
    "hooks": "/hooks",
    "help": "/help",
    "?": "/help",
    "quit": "/quit",
    "trial": "/trial",
}
_BARE_GEAR = re.compile(r"(use|equip|unequip)\s+\S+", re.I)
_BARE_INSPECT = re.compile(r"inspect(\s+\S+)?", re.I)
_HELP = (
    "Describe what you do in your own words; the scene names the odds of what your character weighs, and a "
    "risky action shows its odds before it rolls. In a fight, type a move's number or your own.\n"
    "Commands: sheet (your character) · hooks (what may come back) · inspect 2 (a fight move, free)\n"
    "use <item> · equip <item> · unequip weapon|armour (gear, no turn)\n"
    "help (this) · quit (saves first). The Oath choices are numbers on the list."
)
_NO_LIST = "There is no list outside a fight; type what you do."
_GO_AHEAD = "Go ahead? (y/n) "
_INSPECT_OUTSIDE = "inspect works on fight moves; outside a fight the scene names the odds."
_SAVED = "Saved. `pantheon play` resumes here."
_FIGHT_ENDS = {
    "victory": "no foe is left standing",
    "fled": "you got away",
    "story": "it broke off",
    "reckoning": "you died",
    "death": "you died",
}
_DEAD = (
    "[bold]This character is dead.[/bold] `pantheon fork N` branches from an earlier turn; "
    "`pantheon play --fresh` starts a new game."
)


def _new(args: argparse.Namespace, console: Console) -> int:
    config = load_config(Path(args.config) if args.config else None)
    world = load_world(config.world_dir)
    if world.data is None:
        console.print("[red]world/data/ is missing; cannot draw the opening gods.[/red]")
        return 1
    with Database.open(Path(args.db) if args.db else config.db_path) as db:
        create_timeline(db, world, config, args.seed, console)
    return 0


def create_timeline(db: Database, world: World, config: Config, seed_arg: int, console: Console) -> str:
    assert world.data is not None
    seed = seed_arg or config.seed or secrets.randbelow(2**62) + 1
    rng = RngStreams.from_seed(seed)
    fixed = config.opening_gods
    gods = draw_opening_gods(rng, world.data.god_ids(), fixed=(fixed[0], fixed[1]) if fixed else None)
    tid = db.create_timeline(
        seed=seed, rng_state=rng.state(), events=[("opening_gods_drawn", {"gods": list(gods)})]
    )
    console.print(f"New timeline [bold]{tid[:8]}[/bold] · seed {seed}")
    return tid


def _pick(ask: Ask, console: Console, title: str, options: list[tuple[str, str]]) -> str:
    """Show a numbered list and return the chosen id. Keeps asking until the answer is valid."""
    console.print(f"\n[bold]{title}[/bold]")
    for number, (_, label) in enumerate(options, 1):
        console.print(f"  {number}. {label}")
    ids = {option_id for option_id, _ in options}
    while True:
        answer = ask("> ").strip()
        if answer.isdecimal() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1][0]
        if answer in ids:
            return answer
        console.print("Pick a number from the list.")


def _assign_stats(ask: Ask, console: Console, array: tuple[int, ...]) -> dict[str, int]:
    console.print(f"\n[bold]Assign your stats[/bold] ({', '.join(str(v) for v in array)})")
    console.print(f"Name the five stats from strongest to weakest: {', '.join(STATS)}.")
    console.print("First letters are enough, such as [bold]a p v i r[/bold]. Press Enter for that order.")
    while True:
        parts = (ask("> ").strip().lower() or "a p v i r").replace(",", " ").split()
        chosen = [next((s for s in STATS if s.startswith(p)), "") for p in parts]
        if sorted(chosen) == sorted(STATS):
            return dict(zip(chosen, array, strict=True))
        console.print("Use each of the five stats once.")


def _create_character(sim: Simulation, ask: Ask, console: Console) -> None:
    data = sim.rules.data
    console.print(Panel("[bold]Who were you, before the fall?[/bold]"))
    name = ""
    while not name:
        name = ask("Name: ").strip()
    age_text = ask("Age, 16 to 30 [22]: ").strip()
    age = int(age_text) if age_text.isdecimal() and 16 <= int(age_text) <= 30 else 22
    people = _pick(ask, console, "Your people", [(p.id, p.name) for p in data.peoples])
    people_stat = None
    if next(p for p in data.peoples if p.id == people).stat == "any":
        people_stat = _pick(ask, console, "Which stat gets your people's +3?", [(s, s) for s in STATS])
    options = innate_affinity_options(sim, people)
    innate = options[0]
    if len(options) > 1:
        innate = _pick(ask, console, "Your innate affinity", [(a, a) for a in options])
    origin = _pick(
        ask,
        console,
        "Your origin",
        [(o.id, f"{o.name}: {o.stat} +2, {o.skill} 1. {o.complication}.") for o in data.origins.origins],
    )
    stats = _assign_stats(ask, console, data.origins.stat_array)
    flaws = "; ".join(data.origins.flaws)
    flaw = ask(f"\nYour flaw ({flaws}, or write one): ").strip() or data.origins.flaws[0]
    debt = ask("Your debt (a sum, a favour or a name owed, and to whom): ").strip() or "A favour owed"
    create_character(
        sim,
        CharacterChoices(
            name=name,
            people=people,
            origin=origin,
            age=age,
            flaw=flaw,
            debt=debt,
            stats=stats,
            people_stat=people_stat,
            innate_affinity=innate,
        ),
    )


def status_line(state: GameState) -> str:
    progress = "Unwritten"
    if state.level:
        progress = f"Tier {state.tier} · Level {state.level} · XP {state.xp}/{xp_to_next(state.level)}"
    health = f"HP {state.hp}/{state.max_hp}" + (" [red]DOWNED[/red]" if state.downed else "")
    return f"[dim]{format_date(date_of(state.day))} · {state.name} · {progress} · {health}[/dim]"


def _bar(label: str, value: int, maximum: int) -> str:
    filled = max(0, round(_BAR_WIDTH * value / maximum)) if maximum else 0
    return f"{label:<8}{'█' * filled}{'░' * (_BAR_WIDTH - filled)} {value}/{maximum}"


def sheet(state: GameState, world: World) -> Panel:
    assert world.data is not None
    current = world.data.class_of(state.class_id)
    oaths = {o.id: o.name for o in world.data.oaths}
    lines = [
        f"[bold]{state.name}[/bold], {state.age}, {state.people}",
        f"Class: {current.name if current else 'none'} · Profession: {state.profession or 'none'}",
        f"Tier {state.tier} · Level {state.level} · {format_date(date_of(state.day))}",
        _bar("HP", state.hp, state.max_hp),
        _bar("Mana", state.mana, state.max_mana),
        _bar("Stamina", state.stamina, state.max_stamina),
        *([_bar("XP", state.xp, xp_to_next(state.level))] if state.level else []),
        f"Purse: {format_cp(state.purse_cp)}",
        " · ".join(f"{s.capitalize()} {state.stats[s]}" for s in STATS),
        "Affinities: " + (", ".join(f"{a} {r}" for a, r in state.affinities.items()) or "none"),
        "Skills: " + (", ".join(f"{s} {r}" for s, r in state.skills.items()) or "none"),
        "Oaths: " + (", ".join(oaths[o] for o in state.oaths) or "none"),
        "Standing: " + (", ".join(f"{e} {v:+d}" for e, v in state.standing.items()) or "none"),
    ]
    trait = trait_of(state, world.data) if world.data else None
    if trait is not None:
        attuned = f" ({state.attunement.capitalize()})" if state.attunement else ""
        lines.insert(2, f"Trait: {trait.name}{attuned}")
    if state.reckonings:
        lines.append(f"Reckonings: {state.reckonings}")
    if state.titles:
        lines.append("Titles: " + ", ".join(state.titles))
    if state.injuries:
        lines.append("Injuries: " + ", ".join(f"{i.stat} -{i.amount}" for i in state.injuries))
    if state.inventory:
        names = {i.id: i.name for i in world.data.items}
        worn = set(state.equipped.values())
        lines.append(
            "Gear: "
            + ", ".join(
                f"{names.get(k, k)}{' x' + str(n) if n > 1 else ''}{' (in use)' if k in worn else ''}"
                for k, n in state.inventory.items()
            )
        )
    if state.shards:
        lines.append(
            "Shards: " + ", ".join(f"{s.target} {'fragment' if s.fragment else s.kind}" for s in state.shards)
        )
    return Panel("\n".join(lines), title="The Ledger" if state.oaths else "Unwritten", border_style="yellow")


def ledger_lines(events: list[EventRecord]) -> list[str]:
    """What the engine decided this turn, shown beside the prose (GAME-04)."""
    lines = []
    for type_, p in events:
        match type_:
            case "check_resolved":
                lines.append(check_notice(p).strip("*"))
            case "xp_gained":
                lines.append(f"+{p['amount']} XP ({p['reason']})")
            case "level_up":
                gains = ", ".join(f"{s} +{g}" for s, g in p["gains"].items())
                lines.append(f"[bold]Level {p['level']}![/bold] {gains}".rstrip())
            case "effect_applied":
                sign = "-" if p["kind"] == "damage" else "+"
                lines.append(f"{sign}{p['amount']} HP ({p['reason']})")
            case "downed":
                lines.append("[red bold]Downed[/red bold]")
            case "standing_changed":
                lines.append(
                    f"Standing with {p['entity']}: {p['delta']:+d}, now {p['value']:+d} ({p['reason']})"
                )
            case "rumour_recorded":
                lines.append(f"Rumour: {p['text']}")
            case "oath_sworn":
                lines.append(
                    f"[bold]Oath sworn:[/bold] {p['oath']}. {p['affinity']} rank {p['affinity_rank']}."
                )
            case "hook_registered":
                lines.append(f"[dim]Consequence noted: {p['description']}[/dim]")
            case "skill_gained":
                lines.append(f"[bold]Skill:[/bold] {p['skill']} rank {p['rank']} ({p['rarity']})")
            case "affinity_raised":
                lines.append(f"[bold]Affinity:[/bold] {p['affinity']} rank {p['rank']}")
            case "shard_gained":
                lines.append(f"Shard: {p['target']} ({p['rarity']})")
            case "title_earned":
                lines.append(f"[bold]Title:[/bold] {p['title']}")
            case "injury_gained":
                lines.append(f"[red bold]Injury:[/red bold] {p['stat']} -{p['amount']} ({p['reason']})")
            case "xp_lost":
                lines.append(f"-{p['amount']} XP ({p['reason']})")
            case "trial_resolved":
                lines.append(f"[bold]Ascension Trial: {p['result'].capitalize()}[/bold]")
            case "class_evolved":
                lines.append(f"[bold]Class evolved:[/bold] {p['class_id']}, {p['stat']} +{p['bonus']}")
            case "time_advanced":
                lines.append(f"[dim]Time passes ({p['reason']}).[/dim]")
            case "clock_advanced":
                state = "[bold]has filled[/bold]" if p["filled"] else "moves"
                lines.append(f"{p['name']} {state}: {p['value']} of {p['segments']}")
            case "petition_resolved":
                lines.append(f"Petition {'granted' if p['granted'] else 'not granted'} ({p['reason']})")
            case "fight_started":
                lines.append(f"[bold]A fight begins:[/bold] {', '.join(f['name'] for f in p['foes'])}")
            case "loot_granted":
                lines.append(f"[bold]Loot[/bold] from {p['source']}:")
            case "currency_changed":
                sign = "+" if p["delta_cp"] > 0 else "-"
                lines.append(f"{sign}{format_cp(abs(p['delta_cp']))} ({p['reason']})")
            case "item_changed":
                sign = "+" if p["quantity"] > 0 else ""
                lines.append(f"{sign}{p['quantity']} {p['item'].replace('_', ' ')} ({p['reason']})")
            case "item_equipped":
                lines.append(f"Equipped: {p['item'].replace('_', ' ')} ({p['slot']})")
            case "item_unequipped":
                lines.append(f"Took off the {p['slot']}")
            case "attuned":
                lines.append(f"[bold]Attuned:[/bold] {p['element'].capitalize()}")
            case "trait_used":
                target = f" on {p['foe']}" if p.get("foe") else ""
                lines.append(f"[bold]{p['trait']}[/bold]{target}: once this fight")
            case "skill_spent" if p["cost"]:
                lines.append(f"{p['skill']}: -{p['cost']} {p['pool']}")
            case "foe_hit":
                lines.append(f"{p['name']} takes {p['hits']} hit{'s' if p['hits'] > 1 else ''}")
            case "overspend_rolled":
                lines.append(f"Overspent {p['skill']}: {p['chance']}% Injury risk, rolled {p['roll']}")
            case "fight_ended":
                lines.append(f"[bold]The fight ends:[/bold] {_FIGHT_ENDS[p['result']]}")
            case "last_breath":
                lines.append(f"[red bold]Last Breath {p['marks']}[/red bold]")
            case "level_lost":
                lines.append(f"[red]Level lost: now Level {p['level']}[/red]")
            case "reckoning":
                lines.append(f"[red bold]Reckoning {p['count']}.[/red bold] You wake at the last shrine.")
            case "died":
                lines.append("[red bold]The Ledger closes. This death is final.[/red bold]")
            case _:
                pass
    return lines


def _player_choices(sim: Simulation, ask: Ask, console: Console) -> None:
    """Choices that belong to the player, asked as soon as they are due."""
    data = sim.rules.data
    if sim.state.needs_class:
        console.print(
            Panel("The Ledger opens: a page in your own handwriting that you do not remember writing.")
        )
        classes = [(c.id, f"{c.name}: {c.primary} / {c.secondary}") for c in data.classes]
        choose_class(sim, _pick(ask, console, "Choose your class", classes))
    trait = trait_of(sim.state, data)
    if trait is not None and needs_attunement(sim.state, data):
        elements = [(e, e.capitalize()) for e in trait.attunements]
        choose_attunement(sim, _pick(ask, console, f"{trait.name}: choose your element", elements))
    if sim.state.needs_profession:
        professions = [(p, p) for p in data.professions.all()]
        choose_profession(sim, _pick(ask, console, "Choose your profession", professions))
    while sim.state.free_points > 0:
        allocate_point(sim, _pick(ask, console, "Place your free point", [(s, s) for s in STATS]))
    names = {s.id: s for s in data.skills}
    while sim.state.skill_offers:
        options = [(o, f"{names[o].name} ({names[o].rarity})") for o in sim.state.skill_offers[0]]
        pick_skill(sim, _pick(ask, console, "Your class offers a skill", options))
    if sim.state.needs_evolution:
        evolutions = [(e.id, e.name) for e in evolution_options(sim.state, data)]
        choose_evolution(sim, _pick(ask, console, "Choose your evolved class", evolutions))


def _show(outcome: TurnOutcome, console: Console) -> None:
    console.print(Panel(Markdown(outcome.narration), border_style="red" if outcome.is_fallback else "blue"))
    for line in ledger_lines(outcome.events):
        if line not in outcome.narration:  # A check the narrator placed in the story is already on screen.
            console.print(f"  {line}")


def odds_text(state: GameState, world: World, action: Action) -> str:
    """The odds on a suggested action, from the same calculation as the roll (D-036)."""
    assert world.data is not None
    return "" if action.check is None else f" {chance(state, world.data, action.check)}"


def show_fight(state: GameState, world: World, console: Console) -> None:
    """Each foe's intent comes from the engine, so the player always sees it (D-014, GAME-04)."""
    assert world.data is not None
    if state.fight is None:
        return
    console.print(f"[bold]Exchange {state.fight.exchange}[/bold]")
    for foe in state.fight.standing:
        hits = f"{foe.hits_left} hit{'s' if foe.hits_left > 1 else ''} left"
        console.print(f"  {foe.name} (Tier {foe.tier}, {hits}) shows {intent_label(world.data, foe.intent)}")
    if state.downed:
        console.print(f"  [red bold]You are Downed.[/red bold] Last Breaths: {state.last_breath}")


def _show_actions(state: GameState, world: World, console: Console) -> None:
    console.print(status_line(state))
    show_fight(state, world, console)
    if state.trial_ready:
        console.print(
            "[bold]An Ascension Trial is ready.[/bold] Type [bold]trial[/bold] when you choose to face it."
        )
    if state.fight is None:
        return  # No menu outside a fight: the scene's closing thought carries the odds (D-050).
    for number, action in enumerate(state.suggested, 1):
        odds = odds_text(state, world, action)
        tag = f"[bold]\\[{action.tag.upper()}{odds}][/bold] " if action.tag else ""
        console.print(f"  {number}. {tag}{action.label}")


def offer_start(state: GameState) -> int:
    """The Dual Offer's first number: after a fight's moves, or 1 when no list is shown (D-050)."""
    return len(state.suggested) + 1 if state.fight is not None else 1


def inspect_option(state: GameState, world: World, rest: str) -> str:
    """Everything known about one option, without using game time."""
    if not rest.strip():
        return "Name an option, such as inspect 2."
    number = int(rest) if rest.isdecimal() else 0
    if not 1 <= number <= len(state.suggested):
        return f"There is no option {rest}."
    action = state.suggested[number - 1]
    lines = [f"[bold]{action.label}[/bold]"]
    if action.check is None:
        lines.append("No roll.")
    else:
        check = action.check
        stat = str(check["stat"])
        skill = f" + {check['skill']}" if check.get("skill") else ""
        odds = odds_text(state, world, action).strip()
        lines.append(
            f"{stat.capitalize()} {state.stats[stat]}{skill} · {check['difficulty']} · "
            f"challenge Tier {check['challenge_tier']} · {odds}"
        )
        if check.get("stakes"):
            lines.append(f"At stake: {check['stakes']}")
    shown_above = {*STATS, (action.check or {}).get("skill")}
    if action.tag and action.tag.lower() not in shown_above:
        lines.append(f"Rests on: {action.tag}")
    if action.cost:
        lines.append(f"Cost or risk: {action.cost}")
    return "\n".join(lines)


def offer_choices(state: GameState, world: World) -> list[tuple[str, str]]:
    """The Dual Offer's choices, which only the player makes: (choice, label)."""
    assert world.data is not None
    if state.offer_resolved:
        return []
    gods = {g.id: g for g in world.data.gods}
    oaths = {o.id: o for o in world.data.oaths}
    choices = [
        (g, f"Swear the {oaths[gods[g].first_oath].name} to {gods[g].name}") for g in state.opening_gods
    ]
    return [*choices, ("refuse", "Refuse both gods")]


def offer_terms(state: GameState, world: World) -> dict[str, str]:
    """Each Dual Offer choice in plain words; the gods' voices stay oblique (D-033)."""
    assert world.data is not None
    gods = {g.id: g for g in world.data.gods}
    oaths = {o.id: o for o in world.data.oaths}
    terms = {"refuse": _REFUSE_TERMS}
    for god in state.opening_gods:
        oath = oaths[gods[god].first_oath]
        terms[god] = f"Gift: {oath.perk}. Burden: {oath.burden}."
    return terms


def spoken_choice(line: str, state: GameState, world: World) -> str | None:
    """Which offer choice a typed line seems to make; the game asks before acting on it."""
    assert world.data is not None
    lowered = line.lower()
    if "?" in lowered:
        return None
    if re.search(r"\brefuse\b.*\b(both|all|you)\b", lowered):
        return "refuse"
    if not re.search(r"\b(swear|accept)\b", lowered):
        return None
    gods = {g.id: g for g in world.data.gods if g.id in state.opening_gods}
    oaths = {o.id: o.name.lower() for o in world.data.oaths}
    named = [g.id for g in gods.values() if g.name.lower() in lowered or oaths[g.first_oath] in lowered]
    return named[0] if len(named) == 1 else None


class Game:
    """One play session. The database is the save: every turn commits before the next prompt."""

    def __init__(
        self,
        db: Database,
        tid: str,
        world: World,
        rules: Rules,
        config: Config,
        client: LLMClient,
        ask: Ask,
        console: Console,
    ) -> None:
        self.db = db
        self.tid = tid
        self.world = world
        self.rules = rules
        self.config = config
        self.client = client
        self.ask = ask
        self.console = console
        self.state = db.load_state(tid)
        self.locks: dict[str, dict[str, Any]] = {}  # This turn's stat locks (D-050), in memory only.
        self.locks_turn = 0

    def _command_sim(self) -> Simulation:
        rng = RngStreams.from_state(self.db.rng_state(self.tid), self.db.seed(self.tid))
        return Simulation(self.state, rng, self.rules, self.db.last_turn(self.tid) + 1)

    def _commit_commands(self, sim: Simulation) -> None:
        if sim.events:
            self.db.commit_events(self.tid, sim.turn, sim.events, sim.rng.state())
        self.state = sim.state

    def player_choices(self) -> None:
        sim = self._command_sim()
        _player_choices(sim, self.ask, self.console)
        self._commit_commands(sim)

    def _take(
        self, player_input: str, turn: int, chosen_check: dict[str, Any] | None, previewed: bool
    ) -> TurnOutcome:
        with self.console.status("The world answers..."):
            return take_turn(
                self.client,
                self.world,
                self.rules,
                self.state,
                self.db.rng_state(self.tid),
                self.db.recent_turns(self.tid, history_window(turn - 1, self.config.recent_turns)),
                player_input,
                turn,
                max_rounds=self.config.max_tool_rounds,
                max_retries=self.config.max_tool_retries,
                violence=self.config.violence,
                chosen_check=chosen_check,
                seed=self.db.seed(self.tid),
                locks=self.locks,
                previewed=previewed,
            )

    def turn(self, player_input: str, chosen_check: dict[str, Any] | None = None) -> None:
        turn = self.db.last_turn(self.tid) + 1
        if self.locks_turn != turn:
            self.locks, self.locks_turn = {}, turn
        outcome = self._take(player_input, turn, chosen_check, previewed=False)
        spent = (0, 0, 0)
        if outcome.preview is not None:  # A Hard check or harder waits for the player (NAR-08).
            assert self.world.data is not None
            self.console.print(
                f"Preview: {escape(preview_text(self.state, self.world.data, outcome.preview))}"
            )
            stakes = outcome.preview.get("stakes")
            at_stake = f"At stake: {stakes}. " if stakes else ""
            self.console.print(f"  {escape(at_stake)}Nothing has been rolled yet.")
            if self.ask(_GO_AHEAD).strip().lower() not in ("y", "yes"):
                self.console.print("You back off. Nothing was rolled or saved.")
                return
            spent = (outcome.tokens_in, outcome.tokens_cached, outcome.tokens_out)
            outcome = self._take(player_input, turn, outcome.preview, previewed=True)
        record = TurnRecord(
            turn,
            player_input,
            outcome.narration,
            outcome.is_fallback,
            outcome.tokens_in + spent[0],
            outcome.tokens_cached + spent[1],
            outcome.tokens_out + spent[2],
        )
        self.db.commit_turn(self.tid, record, outcome.events, outcome.rng_state, outcome.state)
        self.state = outcome.state
        _show(outcome, self.console)
        self.player_choices()
        if any(type_ == "level_up" for type_, _ in outcome.events):
            self.console.print(sheet(self.state, self.world))

    def _gear(self, verb: str, what: str) -> None:
        """Use, equip or unequip through the engine, with no turn (D-047); a refusal changes nothing."""
        handlers = {"use": use_item, "equip": equip_item, "unequip": unequip_item}
        sim = self._command_sim()
        try:
            handlers[verb](sim, what)
        except Rejected as exc:
            self.console.print(f"[red]{escape(str(exc))}[/red]")
            return
        self._commit_commands(sim)
        for line in ledger_lines(sim.events):
            self.console.print(f"  {line}")

    def _settle_offer(self, choice: str) -> str | None:
        sim = self._command_sim()
        try:
            result = resolve_offer(sim, choice)
        except Rejected as exc:
            self.console.print(f"[yellow]{exc}[/yellow]")
            return None
        self._commit_commands(sim)
        for line in ledger_lines(sim.events):
            self.console.print(f"  {line}")
        self.player_choices()
        if result["sworn"]:
            self.console.print(sheet(self.state, self.world))
            return (
                f"[I swear the {result['sworn']} Oath to {choice}. The Ledger opens. Narrate the aftermath.]"
            )
        return "[I refuse both gods and stay Unwritten. Narrate the aftermath.]"

    def _attempt_trial(self) -> str | None:
        sim = self._command_sim()
        try:
            result = attempt_trial(sim)
        except Rejected as exc:
            self.console.print(f"[yellow]{exc}[/yellow]")
            return None
        self._commit_commands(sim)  # Saved before any prompt, so closing the game cannot undo the roll.
        for line in ledger_lines(sim.events):
            self.console.print(f"  {line}")
        self.player_choices()
        if result["result"] == "ascend":
            self.console.print(sheet(self.state, self.world))
        return (
            f"[I face the Ascension Trial and the result is {result['result']}. Narrate it and what follows.]"
        )

    def _command(self, line: str) -> str | None:
        """Return the text to send to the narrator, or None when the command needs no turn."""
        command, _, rest = line.partition(" ")
        match command.lower():
            case "/sheet":
                self.console.print(sheet(self.state, self.world))
            case "/inspect":
                if self.state.fight is None:  # Odds outside a fight come only from the scene (D-050).
                    self.console.print(
                        "inspect works on fight moves; outside a fight the scene names the odds."
                    )
                else:
                    self.console.print(inspect_option(self.state, self.world, rest))
            case "/trial":
                return self._attempt_trial()
            case "/hooks":
                for hook in (h for h in self.state.hooks if not h.resolved):
                    self.console.print(
                        f"  {hook.id}. {hook.description} [dim](due {hook.due_condition})[/dim]"
                    )
            case "/swear":
                if rest:
                    return self._settle_offer(rest)
                self.console.print("Use the numbers on the list to swear an Oath.")
            case "/refuse":
                return self._settle_offer("refuse")
            case "/use" | "/equip" | "/unequip":
                self._gear(command[1:].lower(), rest.strip())
            case _:
                self.console.print(_HELP)
        return None

    def run(self) -> None:
        if self.db.last_turn(self.tid) == 0:
            self.console.print(_HELP)
            self.turn(OPENING_INPUT)
        else:
            last = self.db.recent_turns(self.tid, 1)[0][1]
            self.console.print(Panel(Markdown(last), border_style="blue"))
            self.player_choices()  # A choice left open by quitting, or by forking at that turn.
        while True:
            if self.state.dead:
                self.console.print(_DEAD)
                return
            _show_actions(self.state, self.world, self.console)
            offers = offer_choices(self.state, self.world)
            first = offer_start(self.state)
            terms = offer_terms(self.state, self.world)
            for number, (choice_id, label) in enumerate(offers, first):
                self.console.print(f"  {number}. [bold]{label}[/bold]")
                self.console.print(f"     [dim]{terms[choice_id]}[/dim]")
            fighting = self.state.fight is not None
            self.console.print(
                "  [dim]Or type your own.[/dim]" if fighting else "  [dim]Type what you do.[/dim]"
            )
            self.console.print(f"  {_FIGHT_COMMANDS if fighting else _COMMANDS}")
            line = self.ask("\nWhat do you do? ").strip()
            if not line:
                continue
            line = _BARE_COMMANDS.get(line.lower(), line)
            if _BARE_INSPECT.fullmatch(line) or _BARE_GEAR.fullmatch(line):
                line = f"/{line}"
            choice = None
            if line.isdecimal() and first <= int(line) < first + len(offers):
                choice = offers[int(line) - first][0]
            elif not line.startswith("/") and not line.isdecimal():
                spoken = spoken_choice(line, self.state, self.world)
                labels = dict(offers)
                if (
                    spoken
                    and self.ask(f"{labels[spoken]}? This cannot be undone. (y/n) ").strip().lower() == "y"
                ):
                    choice = spoken
            if choice:
                text = self._settle_offer(choice)
                if text:
                    self.turn(text)
                continue
            if line.lower() == "/quit":
                self.console.print(_SAVED)
                return
            chosen_check = None
            if line.isdecimal() and not fighting:
                self.console.print(_NO_LIST)
                continue
            if line.isdecimal() and 1 <= int(line) <= len(self.state.suggested):
                action = self.state.suggested[int(line) - 1]
                chosen_check = action.check
                line = f"{action.label} ({action.tag})" if action.tag and not action.check else action.label
            elif line.startswith("/"):
                text = self._command(line)
                if text is None:
                    continue
                line = text
            self.turn(line, chosen_check)


def _play(args: argparse.Namespace, console: Console, ask: Ask, client: LLMClient | None) -> int:
    config = load_config(Path(args.config) if args.config else None)
    world = load_world(config.world_dir)
    assert world.data is not None
    if client is None:
        if not config.narrator_model:
            console.print(
                "[red]Set the narrator under [models] in config.toml (see config.example.toml).[/red]"
            )
            return 1
        if not config.base_url and not os.environ.get("ANTHROPIC_API_KEY"):
            console.print(
                "[red]No API key. Put ANTHROPIC_API_KEY=... in a .env file next to start.bat.[/red]"
            )
            return 1
        client = AnthropicClient(config.narrator_model, config.base_url, config.think)
    rules = Rules(world.data, {k: f.set_by for k, f in world.flags.items()}, config.permadeath)
    with Database.open(Path(args.db) if args.db else config.db_path) as db:
        tid = db.find_timeline(args.timeline) if args.timeline else db.latest_timeline()
        if tid is None or args.fresh:
            tid = create_timeline(db, world, config, args.seed, console)
        try:
            state = db.load_state(tid)
            if not state.created:
                rng = RngStreams.from_state(db.rng_state(tid), db.seed(tid))
                sim = Simulation(state, rng, rules, 0)
                _create_character(sim, ask, console)
                db.commit_events(tid, 0, sim.events, rng.state())
            Game(db, tid, world, rules, config, client, ask, console).run()
        except (EOFError, KeyboardInterrupt):
            console.print(f"\n{_SAVED}")
    return 0


def _fork(args: argparse.Namespace, console: Console) -> int:
    config = load_config(Path(args.config) if args.config else None)
    with Database.open(Path(args.db) if args.db else config.db_path) as db:
        parent = db.find_timeline(args.timeline) if args.timeline else db.latest_timeline()
        if parent is None:
            console.print("[red]There is no timeline to fork yet.[/red]")
            return 1
        tid = db.fork(parent, args.turn)
    console.print(
        f"New timeline [bold]{tid[:8]}[/bold] from turn {args.turn} of {parent[:8]}. "
        f"`pantheon play` continues it; `pantheon play --timeline {parent[:8]}` returns to the original."
    )
    return 0


def _roll(args: argparse.Namespace, console: Console) -> int:
    """`pantheon roll`: a d100 check by the engine's own rules, outside any game (M1f, no LLM)."""
    rng = RngStreams.from_seed(args.seed)
    request = CheckRequest(
        difficulty=Difficulty(args.difficulty),
        stat=args.stat,
        skill_rank=args.skill,
        actor_tier=args.tier,
        challenge_tier=args.challenge,
        approach=Approach(args.approach),
        bonus=args.bonus,
    )
    try:
        odds = check_odds(request)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    shown = "settled by the tier gap" if odds.shown is None else f"{odds.shown}% shown ({odds.chance} raw)"
    console.print(f"Tier gap {odds.tier_gap:+d}, chance {shown}, seed {args.seed}")
    for _ in range(args.count):
        result = resolve_check(rng, request)
        rolled = "no roll" if result.roll is None else f"rolled {result.roll:02d}"
        extra = " + complication" if result.complication else ""
        console.print(f"  {rolled}: {result.outcome.value.replace('_', ' ')}{extra}")
    return 0


def _timeline(db: Database, prefix: str | None, console: Console) -> str | None:
    tid = db.find_timeline(prefix) if prefix else db.latest_timeline()
    if tid is None:
        console.print("[red]There is no timeline yet. Start one with `pantheon play`.[/red]")
    return tid


def _show_sheet(args: argparse.Namespace, console: Console) -> int:
    """`pantheon sheet`: the character sheet of a timeline, read from the save (M1f)."""
    config = load_config(Path(args.config) if args.config else None)
    world = load_world(config.world_dir)
    with Database.open(Path(args.db) if args.db else config.db_path) as db:
        tid = _timeline(db, args.timeline, console)
        if tid is None:
            return 1
        state = db.load_state(tid)
    console.print(sheet(state, world))
    show_fight(state, world, console)
    return 0


def _log(args: argparse.Namespace, console: Console) -> int:
    """`pantheon log`: the recorded events, turn by turn, as the Ledger shows them (M1f, GAME-04)."""
    config = load_config(Path(args.config) if args.config else None)
    with Database.open(Path(args.db) if args.db else config.db_path) as db:
        tid = _timeline(db, args.timeline, console)
        if tid is None:
            return 1
        logged = db.events(tid)
    if args.turn is not None:
        logged = [e for e in logged if e["turn"] == args.turn]
    if args.type:
        logged = [e for e in logged if e["type"] == args.type]
    shown = logged[-args.last :] if args.last else logged
    console.print(f"[dim]Timeline {tid[:8]}: {len(shown)} of {len(logged)} events[/dim]")
    for event in shown:
        lines = ledger_lines([(event["type"], event["payload"])])
        text = lines[0] if lines else escape(json.dumps(event["payload"], separators=(",", ":")))
        console.print(f"[dim]t{event['turn']:<4}{event['type']:<22}[/dim] {text}")
    return 0


def _chronicle(args: argparse.Namespace, console: Console) -> int:
    """`pantheon chronicle`: the story so far as Markdown or a phone page, read from the save."""
    from pantheon.ui import chronicle  # It builds on this module's sheet and Ledger, so it loads after them.

    config = load_config(Path(args.config) if args.config else None)
    world = load_world(config.world_dir)
    with Database.open(Path(args.db) if args.db else config.db_path) as db:
        tid = _timeline(db, args.timeline, console)
        if tid is None:
            return 1
        built = chronicle.build(db, world, tid)
    text = chronicle.render_html(built) if args.format == "html" else chronicle.render_markdown(built)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        console.print(f"Wrote {args.out}: {len(built.entries)} turns of {built.name}.")
    else:
        print(text)
    return 0


def main(argv: list[str] | None = None, ask: Ask | None = None, client: LLMClient | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pantheon")
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="create a timeline")
    play = sub.add_parser("play", help="play the latest timeline; a new game starts when there is none")
    fork = sub.add_parser("fork", help="branch a new timeline from the end of a turn")
    fork.add_argument("turn", type=int, help="the turn to branch from")
    roll = sub.add_parser("roll", help="roll a check by the engine's rules, outside any game")
    roll.add_argument("--stat", type=int, default=30, help="the stat's value")
    roll.add_argument("--difficulty", choices=[d.value for d in Difficulty], default="routine")
    roll.add_argument("--tier", type=int, default=1, help="the character's tier")
    roll.add_argument("--challenge", type=int, default=1, help="the challenge's tier")
    roll.add_argument("--skill", type=int, default=0, help="the skill's rank")
    roll.add_argument("--approach", choices=[a.value for a in Approach], default="other")
    roll.add_argument("--bonus", type=int, default=0, help="a trait or gear bonus")
    roll.add_argument("--count", type=int, default=1, help="how many rolls")
    roll.add_argument("--seed", type=int, default=1)
    sheet = sub.add_parser("sheet", help="show a timeline's character sheet")
    log = sub.add_parser("log", help="show a timeline's recorded events")
    chronicle = sub.add_parser("chronicle", help="the story so far, as Markdown or a page")
    chronicle.add_argument("--format", choices=["md", "html"], default="md")
    chronicle.add_argument("--out", help="write here instead of printing")
    log.add_argument("--turn", type=int, help="only this turn")
    log.add_argument("--type", help="only this event type, such as xp_gained")
    log.add_argument("--last", type=int, help="only the last N events")
    for command in (new, play):
        command.add_argument("--seed", type=int, default=0, help="seed (0 = config or random)")
    for command in (new, play, fork, sheet, log, chronicle):
        command.add_argument("--db", help="database path (default: data/pantheon.db)")
        command.add_argument("--config", help="config file (default: config.toml)")
    for command in (play, fork, sheet, log, chronicle):
        command.add_argument("--timeline", help="the start of a timeline's id (default: the latest)")
    play.add_argument("--fresh", action="store_true", help="start a new timeline instead of resuming")
    from pantheon.ui.cli import session  # It builds on this module's screens, so it loads after them.

    session.add_parser(sub)
    args = parser.parse_args(argv)
    console = Console()
    try:
        if args.command == "session":
            # Claude Code reads this output, so lines are not wrapped to a terminal's width.
            return session.run(args, Console(soft_wrap=True, highlight=False))
        if args.command == "new":
            return _new(args, console)
        if args.command == "fork":
            return _fork(args, console)
        if args.command == "roll":
            return _roll(args, console)
        if args.command == "sheet":
            return _show_sheet(args, console)
        if args.command == "log":
            return _log(args, console)
        if args.command == "chronicle":
            return _chronicle(args, console)
        return _play(args, console, ask or console.input, client)
    except SaveError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
