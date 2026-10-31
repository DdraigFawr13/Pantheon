"""`pantheon` command line: `new` creates a timeline; `play` runs character creation and the game."""

from __future__ import annotations

import argparse
import os
import re
import secrets
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from pantheon.config import Config, load_config
from pantheon.engine.checks import Outcome
from pantheon.engine.commands import (
    CharacterChoices,
    allocate_point,
    choose_class,
    choose_profession,
    create_character,
    innate_affinity_options,
)
from pantheon.engine.opening import draw_opening_gods
from pantheon.engine.progression import choose_evolution, evolution_options, pick_skill
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import STATS, Action, EventRecord, GameState, xp_to_next
from pantheon.engine.timeline import Rejected, Rules, Simulation
from pantheon.engine.tools import attempt_trial, check_preview, resolve_offer
from pantheon.llm.anthropic_adapter import AnthropicClient
from pantheon.llm.client import LLMClient
from pantheon.narrator.assemble import history_window
from pantheon.narrator.loop import TurnOutcome, take_turn
from pantheon.narrator.notices import check_notice
from pantheon.storage.db import Database, TurnRecord
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
_COMMANDS = "[dim]Commands: inspect 2 · sheet · hooks · help · quit[/dim]"
_BARE_COMMANDS = {
    "sheet": "/sheet",
    "hooks": "/hooks",
    "help": "/help",
    "?": "/help",
    "quit": "/quit",
    "trial": "/trial",
}
_BARE_INSPECT = re.compile(r"inspect(\s+\S+)?", re.I)
_HELP = (
    "Type a number from the list, or describe what you do in your own words.\n"
    "Commands: inspect 2 (look at option 2, free) · sheet (your character) · hooks (what may come back)\n"
    "help (this) · quit (saves first). The Oath choices are numbers on the list."
)
_SAVED = "Saved. `pantheon play` resumes here."


def _new(args: argparse.Namespace, console: Console) -> int:
    config = load_config(Path(args.config) if args.config else None)
    world = load_world(config.world_dir)
    if world.data is None:
        console.print("[red]world/data/ is missing; cannot draw the opening gods.[/red]")
        return 1
    with Database.open(Path(args.db) if args.db else config.db_path) as db:
        _create_timeline(db, world, config, args.seed, console)
    return 0


def _create_timeline(db: Database, world: World, config: Config, seed_arg: int, console: Console) -> str:
    assert world.data is not None
    seed = seed_arg or config.seed or secrets.randbelow(2**62) + 1
    rng = RngStreams.from_seed(seed)
    fixed = config.opening_gods
    gods = draw_opening_gods(rng, world.data.god_ids(), fixed=(fixed[0], fixed[1]) if fixed else None)
    tid = db.create_timeline(seed=seed, rng_state=rng.state())
    db.append_event(tid, turn=0, type_="opening_gods_drawn", payload={"gods": list(gods)})
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
        if answer.isdigit() and 1 <= int(answer) <= len(options):
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
    age = int(age_text) if age_text.isdigit() and 16 <= int(age_text) <= 30 else 22
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


def _status_line(state: GameState) -> str:
    progress = "Unwritten"
    if state.level:
        progress = f"Tier {state.tier} · Level {state.level} · XP {state.xp}/{xp_to_next(state.level)}"
    health = f"HP {state.hp}/{state.max_hp}" + (" [red]DOWNED[/red]" if state.downed else "")
    return f"[dim]{state.name} · {progress} · {health}[/dim]"


def _bar(label: str, value: int, maximum: int) -> str:
    filled = round(_BAR_WIDTH * value / maximum) if maximum else 0
    return f"{label:<8}{'█' * filled}{'░' * (_BAR_WIDTH - filled)} {value}/{maximum}"


def _sheet(state: GameState, world: World) -> Panel:
    assert world.data is not None
    current = world.data.class_of(state.class_id)
    oaths = {o.id: o.name for o in world.data.oaths}
    lines = [
        f"[bold]{state.name}[/bold], {state.age}, {state.people}",
        f"Class: {current.name if current else 'none'} · Profession: {state.profession or 'none'}",
        f"Tier {state.tier} · Level {state.level}",
        _bar("HP", state.hp, state.max_hp),
        _bar("Mana", state.max_mana, state.max_mana),
        _bar("Stamina", state.max_stamina, state.max_stamina),
        *([_bar("XP", state.xp, xp_to_next(state.level))] if state.level else []),
        f"Coin: {state.coin} silver",
        " · ".join(f"{s.capitalize()} {state.stats[s]}" for s in STATS),
        "Affinities: " + (", ".join(f"{a} {r}" for a, r in state.affinities.items()) or "none"),
        "Skills: " + (", ".join(f"{s} {r}" for s, r in state.skills.items()) or "none"),
        "Oaths: " + (", ".join(oaths[o] for o in state.oaths) or "none"),
        "Standing: " + (", ".join(f"{e} {v:+d}" for e, v in state.standing.items()) or "none"),
    ]
    if state.titles:
        lines.append("Titles: " + ", ".join(state.titles))
    if state.injuries:
        lines.append("Injuries: " + ", ".join(f"{i.stat} -{i.amount}" for i in state.injuries))
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


def _odds_text(state: GameState, world: World, action: Action) -> str:
    """The odds on a suggested action, from the same calculation as the roll (D-036)."""
    assert world.data is not None
    if action.check is None:
        return ""
    odds = check_preview(state, world.data, action.check)
    if odds.shown is not None:
        return f" {odds.shown}%"
    return " sure" if odds.outcome is Outcome.SUCCESS else " no chance"


def _show_actions(state: GameState, world: World, console: Console) -> None:
    console.print(_status_line(state))
    if state.trial_ready:
        console.print(
            "[bold]An Ascension Trial is ready.[/bold] Type [bold]trial[/bold] when you choose to face it."
        )
    for number, action in enumerate(state.suggested, 1):
        odds = _odds_text(state, world, action)
        tag = f"[bold]\\[{action.tag.upper()}{odds}][/bold] " if action.tag else ""
        console.print(f"  {number}. {tag}{action.label}")


def _inspect(state: GameState, world: World, rest: str) -> str:
    """Everything known about one option, without using game time."""
    if not rest.strip():
        return "Name an option, such as inspect 2."
    number = int(rest) if rest.isdigit() else 0
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
        odds = _odds_text(state, world, action).strip()
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

    def _command_sim(self) -> Simulation:
        rng = RngStreams.from_state(self.db.rng_state(self.tid))
        return Simulation(self.state, rng, self.rules, self.db.last_turn(self.tid) + 1)

    def _commit_commands(self, sim: Simulation) -> None:
        if sim.events:
            self.db.commit_events(self.tid, sim.turn, sim.events, sim.rng.state())
        self.state = sim.state

    def player_choices(self) -> None:
        sim = self._command_sim()
        _player_choices(sim, self.ask, self.console)
        self._commit_commands(sim)

    def turn(self, player_input: str, chosen_check: dict[str, Any] | None = None) -> None:
        turn = self.db.last_turn(self.tid) + 1
        with self.console.status("The world answers..."):
            outcome = take_turn(
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
            )
        record = TurnRecord(
            turn,
            player_input,
            outcome.narration,
            outcome.is_fallback,
            outcome.tokens_in,
            outcome.tokens_cached,
            outcome.tokens_out,
        )
        self.db.commit_turn(self.tid, record, outcome.events, outcome.rng_state, outcome.state)
        self.state = outcome.state
        _show(outcome, self.console)
        self.player_choices()
        if any(type_ == "level_up" for type_, _ in outcome.events):
            self.console.print(_sheet(self.state, self.world))

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
            self.console.print(_sheet(self.state, self.world))
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
            self.console.print(_sheet(self.state, self.world))
        return (
            f"[I face the Ascension Trial and the result is {result['result']}. Narrate it and what follows.]"
        )

    def _command(self, line: str) -> str | None:
        """Return the text to send to the narrator, or None when the command needs no turn."""
        command, _, rest = line.partition(" ")
        match command.lower():
            case "/sheet":
                self.console.print(_sheet(self.state, self.world))
            case "/inspect":
                self.console.print(_inspect(self.state, self.world, rest))
            case "/trial":
                return self._attempt_trial()
            case "/hooks":
                for hook in self.state.hooks:
                    self.console.print(
                        f"  {hook.id}. {hook.description} [dim](due {hook.due_condition})[/dim]"
                    )
            case "/swear":
                if rest:
                    return self._settle_offer(rest)
                self.console.print("Use the numbers on the list to swear an Oath.")
            case "/refuse":
                return self._settle_offer("refuse")
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
        while True:
            _show_actions(self.state, self.world, self.console)
            offers = offer_choices(self.state, self.world)
            first = len(self.state.suggested) + 1
            terms = offer_terms(self.state, self.world)
            for number, (choice_id, label) in enumerate(offers, first):
                self.console.print(f"  {number}. [bold]{label}[/bold]")
                self.console.print(f"     [dim]{terms[choice_id]}[/dim]")
            self.console.print("  [dim]Or type your own.[/dim]")
            self.console.print(f"  {_COMMANDS}")
            line = self.ask("\nWhat do you do? ").strip()
            if not line:
                continue
            line = _BARE_COMMANDS.get(line.lower(), line)
            if _BARE_INSPECT.fullmatch(line):
                line = f"/{line}"
            choice = None
            if line.isdigit() and first <= int(line) < first + len(offers):
                choice = offers[int(line) - first][0]
            elif not line.startswith("/") and not line.isdigit():
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
            if line.isdigit() and 1 <= int(line) <= len(self.state.suggested):
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
    rules = Rules(world.data, {k: f.set_by for k, f in world.flags.items()})
    with Database.open(Path(args.db) if args.db else config.db_path) as db:
        tid = db.latest_timeline()
        if tid is None or args.fresh:
            tid = _create_timeline(db, world, config, args.seed, console)
        try:
            state = db.load_state(tid)
            if not state.created:
                rng = RngStreams.from_state(db.rng_state(tid))
                sim = Simulation(state, rng, rules, 0)
                _create_character(sim, ask, console)
                db.commit_events(tid, 0, sim.events, rng.state())
            Game(db, tid, world, rules, config, client, ask, console).run()
        except (EOFError, KeyboardInterrupt):
            console.print(f"\n{_SAVED}")
    return 0


def main(argv: list[str] | None = None, ask: Ask | None = None, client: LLMClient | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pantheon")
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="create a timeline")
    play = sub.add_parser("play", help="play the latest timeline; a new game starts when there is none")
    for command in (new, play):
        command.add_argument("--seed", type=int, default=0, help="seed (0 = config or random)")
        command.add_argument("--db", help="database path (default: data/pantheon.db)")
        command.add_argument("--config", help="config file (default: config.toml)")
    play.add_argument("--fresh", action="store_true", help="start a new timeline instead of resuming")
    args = parser.parse_args(argv)
    console = Console()
    if args.command == "new":
        return _new(args, console)
    return _play(args, console, ask or console.input, client)


if __name__ == "__main__":
    sys.exit(main())
