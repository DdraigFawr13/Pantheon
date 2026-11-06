"""`pantheon session`: the Claude Code session is the narrator, one command per turn step (D-041).

Each step is a separate process, so the pending turn is a small JSON file next to the database: the player's
input, the chosen check, every tool call in order and the accepted prose. Every step rebuilds the simulation
from the saved state and replays those calls, so the dice come out the same and nothing is saved until
`commit` (OPS-03). The engine still decides every number (ENG-01, ENG-02).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markup import escape
from rich.text import Text

from pantheon.config import Config, load_config
from pantheon.engine.calendar import clock_value, date_of, format_date
from pantheon.engine.commands import (
    CharacterChoices,
    allocate_point,
    choose_attunement,
    choose_class,
    choose_profession,
    create_character,
    innate_affinity_options,
)
from pantheon.engine.progression import choose_evolution, evolution_options, pick_skill
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import STATS, GameState, xp_to_next
from pantheon.engine.timeline import Rejected, Rules, Simulation
from pantheon.engine.tools import ToolResult, apply_tool, attempt_trial, resolve_offer, tool_definition
from pantheon.engine.traits import needs_attunement, trait_of
from pantheon.narrator.assemble import _REMINDER, _due_material, assemble, state_view
from pantheon.narrator.loop import (
    _NARRATE_OUTCOME,
    _OUTCOME_MEANINGS,
    _REFEREE_PROMPT,
    _SCRIBE_PROMPT,
    _SCRIBE_TOOLS,
    _SUGGEST_PROMPT,
    _numbers_in,
)
from pantheon.narrator.notices import CHECK_MARKER, place_notices
from pantheon.narrator.validators import prose_problems, repeats_earlier_turn, strip_action_list
from pantheon.storage.db import Database, TurnRecord
from pantheon.ui.cli.app import (
    OPENING_INPUT,
    _create_timeline,
    _inspect,
    _odds_text,
    _sheet,
    _status_line,
    ledger_lines,
    offer_choices,
    offer_terms,
)
from pantheon.world.loader import World, load_world

PLAYING = ".playing"
_RECENT_SHOWN = 2


class SessionError(RuntimeError):
    """A step the session cannot take now; the message says what to do instead."""


@dataclass
class Pending:
    """A turn in progress. Only the inputs are kept; every result is replayed from them."""

    timeline: str
    turn: int
    player_input: str
    chosen_check: dict[str, Any] | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)
    narration: str | None = None

    @property
    def talk_only(self) -> bool:
        return self.player_input.startswith("[")


@dataclass
class Replay:
    sim: Simulation
    results: list[ToolResult]
    allowed: set[int]
    outcomes: list[str]


class Session:
    def __init__(self, db: Database, db_path: Path, world: World, config: Config, console: Console) -> None:
        assert world.data is not None
        self.db = db
        self.db_path = db_path
        self.world = world
        self.config = config
        self.console = console
        self.rules = Rules(world.data, {k: f.set_by for k, f in world.flags.items()})

    # Files beside the database.

    @property
    def pending_path(self) -> Path:
        return self.db_path.with_name(self.db_path.stem + ".turn.json")

    @property
    def marker(self) -> Path:
        return self.db_path.parent / PLAYING

    def load_pending(self) -> Pending | None:
        if not self.pending_path.exists():
            return None
        return Pending(**json.loads(self.pending_path.read_text(encoding="utf-8")))

    def save_pending(self, pending: Pending) -> None:
        self.pending_path.write_text(json.dumps(pending.__dict__, indent=1), encoding="utf-8")

    def need_pending(self) -> Pending:
        pending = self.load_pending()
        if pending is None:
            raise SessionError("No turn is in progress. Start one with `session begin`.")
        return pending

    def timeline(self) -> str:
        tid = self.db.latest_timeline()
        if tid is None:
            raise SessionError("There is no game yet. Run `session create` first.")
        return tid

    def state(self) -> GameState:
        return self.db.load_state(self.timeline())

    def command_sim(self) -> Simulation:
        tid = self.timeline()
        rng = RngStreams.from_state(self.db.rng_state(tid))
        return Simulation(self.db.load_state(tid), rng, self.rules, self.db.last_turn(tid) + 1)

    def commit_commands(self, sim: Simulation) -> None:
        if sim.events:
            self.db.commit_events(self.timeline(), sim.turn, sim.events, sim.rng.state())

    def no_pending(self) -> None:
        if self.pending_path.exists():
            raise SessionError(
                "A turn is in progress. Finish it with `session commit` or drop it with `abandon`."
            )

    # The turn, replayed from its inputs.

    def replay(self, pending: Pending) -> Replay:
        tid = pending.timeline
        if tid != self.db.latest_timeline() or pending.turn != self.db.last_turn(tid) + 1:
            raise SessionError("The save moved on since this turn began. Run `session abandon`.")
        state = self.db.load_state(tid)
        sim = Simulation(state, RngStreams.from_state(self.db.rng_state(tid)), self.rules, pending.turn)
        allowed = _numbers_in(state_view(state))  # Prose may quote the engine's own sheet (D-033).
        outcomes: list[str] = []
        if pending.chosen_check is not None:
            chosen = apply_tool(sim, "request_check", pending.chosen_check)
            if chosen.accepted:
                allowed |= _numbers_in(chosen.data)
                outcomes.append(chosen.data["outcome"])
        results = []
        for call in pending.calls:
            result = apply_tool(sim, call["name"], call["args"])
            results.append(result)
            if result.accepted:
                allowed |= _numbers_in(result.data)
                if "outcome" in result.data:
                    outcomes.append(result.data["outcome"])
        return Replay(sim, results, allowed, outcomes)

    def offered(self, pending: Pending, run: Replay) -> tuple[str, ...]:
        """The tools this step allows, by the same rules as the API loop (D-031)."""
        state = run.sim.state
        if pending.narration is None:
            rolled = pending.chosen_check is not None
            return () if rolled or not state.offer_resolved or pending.talk_only else ("request_check",)
        names = _SCRIBE_TOOLS if state.offer_resolved else ("suggest_actions",)
        if not run.sim.checks:  # XP rewards a tested deed, so a talking turn cannot farm it.
            names = tuple(n for n in names if n != "grant_xp")
        return names

    def begin(self, player_input: str, option: int | None) -> None:
        self.no_pending()
        tid = self.timeline()
        state = self.db.load_state(tid)
        if not state.created:
            raise SessionError("Create the character first with `session create`.")
        due = self.choices_due(state)
        if due:
            raise SessionError(
                "The player must choose first (`session choose <kind> <id>`): " + "; ".join(due)
            )
        chosen = None
        if option is not None:
            if not 1 <= option <= len(state.suggested):
                raise SessionError(f"There is no option {option}.")
            action = state.suggested[option - 1]
            chosen = action.check
            player_input = f"{action.label} ({action.tag})" if action.tag and not chosen else action.label
        if not player_input:
            player_input = OPENING_INPUT if self.db.last_turn(tid) == 0 else ""
        if not player_input:
            raise SessionError("Say what the player does, or pass --option N.")
        pending = Pending(tid, self.db.last_turn(tid) + 1, player_input, chosen)
        run = self.replay(pending)
        if chosen is not None and not run.outcomes:
            pending.chosen_check = None  # The check no longer applies; the referee may roll a fresh one.
            run = self.replay(pending)
        self.save_pending(pending)
        self.brief(pending, run)

    def brief(self, pending: Pending, run: Replay) -> None:
        """What the API narrator would see this turn, minus the canon prefix (`session prompt`)."""
        state = self.db.load_state(pending.timeline)
        out = self.console.print
        out(f"[bold]Turn {pending.turn}[/bold] · timeline {pending.timeline[:8]}")
        recent = self.db.recent_turns(pending.timeline, _RECENT_SHOWN)
        for said, narration in recent:
            out(f"\n[dim]Earlier, the player: {escape(said)}[/dim]\n{escape(narration)}")
        out(f"\n[Character sheet: {json.dumps(state_view(state), separators=(',', ':'))}]")
        out(f"[Due: {escape(_due_material(state, self.world))}]")
        out(f"\nThe player: {escape(pending.player_input)}\n\n{escape(_REMINDER)}")
        self.next_step(pending, run)

    def next_step(self, pending: Pending, run: Replay) -> None:
        out = self.console.print
        if run.outcomes and pending.narration is None:
            note = ", then ".join(_OUTCOME_MEANINGS[o] for o in run.outcomes)
            for type_, payload in run.sim.events:
                if type_ == "check_resolved":
                    out(f"Engine check: {escape(json.dumps(payload))}")
            out(escape(_NARRATE_OUTCOME.format(outcomes=note)))
        names = self.offered(pending, run)
        if pending.narration is None:
            if names and not run.outcomes:
                out(escape(_REFEREE_PROMPT.replace("reply with the single word NONE", "write the prose")))
                out("Step: `session tool request_check '{...}'` if it is a check, else write the prose.")
            out("Step: write the prose to data/narration.md, then `session narrate data/narration.md`.")
            return
        if run.sim.suggested:
            out(f"Options recorded. Other tools now: {', '.join(names)}. Then `session commit`.")
            return
        out(escape(_SCRIBE_PROMPT if len(names) > 1 else _SUGGEST_PROMPT))
        out(f"Tools now: {', '.join(names)}. `session tools` shows their fields.")
        out("Step: `session tool <name> '<json>'` for each, then `session commit`.")

    def tool(self, name: str, raw: str) -> None:
        pending = self.need_pending()
        run = self.replay(pending)
        names = self.offered(pending, run)
        try:
            args = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SessionError(f"The arguments are not JSON: {exc}") from exc
        if name not in names:
            raise SessionError(f"{name} is not available now. Tools now: {', '.join(names) or 'none'}.")
        before = len(run.sim.events)
        result = apply_tool(run.sim, name, args)
        if not result.accepted:
            self.console.print(f"[yellow]Rejected: {escape(result.reason)}[/yellow]")  # NAR-06: nothing kept.
            return
        pending.calls.append({"name": name, "args": args})
        self.save_pending(pending)
        self.console.print(escape(json.dumps(result.payload())))
        for line in ledger_lines(run.sim.events[before:]):
            self.console.print(f"  {line}")
        self.next_step(pending, self.replay(pending))

    def narrate(self, path: Path) -> None:
        pending = self.need_pending()
        if pending.narration is not None:
            raise SessionError("This turn already has its prose. Record its consequences, then commit.")
        run = self.replay(pending)
        text = strip_action_list(path.read_text(encoding="utf-8")).strip()
        problems = ["the prose is empty"] if not text else prose_problems(text, run.allowed)
        recent = [n for _, n in self.db.recent_turns(pending.timeline, self.config.recent_turns)]
        if repeats_earlier_turn(text, recent):
            problems.append("it repeats earlier narration; answer what the player just did with new events")
        if run.outcomes and CHECK_MARKER not in text:
            problems.append(f"put {CHECK_MARKER} on its own line where the check's result lands")
        if problems:
            self.console.print("[yellow]Not accepted: " + escape("; ".join(problems)) + ".[/yellow]")
            return
        pending.narration = place_notices(text, run.sim.events)
        self.save_pending(pending)
        self.console.print("Prose accepted.")
        self.next_step(pending, run)

    def commit(self) -> None:
        pending = self.need_pending()
        run = self.replay(pending)
        if pending.narration is None:
            raise SessionError("Write and `narrate` the prose before committing.")
        if not run.sim.suggested:
            raise SessionError("Call suggest_actions before committing: the player needs options.")
        record = TurnRecord(pending.turn, pending.player_input, pending.narration, False, 0, 0, 0)
        self.db.commit_turn(pending.timeline, record, run.sim.events, run.sim.rng.state(), run.sim.state)
        self.pending_path.unlink()
        self.console.print(escape(pending.narration))
        for line in ledger_lines(run.sim.events):
            if line not in pending.narration:
                self.console.print(f"  {line}")
        if any(type_ == "level_up" for type_, _ in run.sim.events):
            self.console.print(_sheet(run.sim.state, self.world))
        self.menu()

    def abandon(self) -> None:
        self.pending_path.unlink(missing_ok=True)
        self.console.print("The turn in progress is dropped; nothing was saved from it.")

    # What the player sees between turns.

    def choices_due(self, state: GameState) -> list[str]:
        assert self.world.data is not None
        data = self.world.data
        due = []
        if state.needs_class:
            due.append("class: " + ", ".join(f"{c.id} ({c.primary}/{c.secondary})" for c in data.classes))
        trait = trait_of(state, data)
        if trait is not None and needs_attunement(state, data):
            due.append(f"attunement ({trait.name}): " + ", ".join(trait.attunements))
        if state.needs_profession:
            due.append("profession: " + ", ".join(data.professions.all()))
        if state.free_points > 0:
            due.append(f"point ({state.free_points} free): " + ", ".join(STATS))
        if state.skill_offers:
            names = {s.id: s for s in data.skills}
            due.append("skill: " + ", ".join(f"{o} ({names[o].rarity})" for o in state.skill_offers[0]))
        if state.needs_evolution:
            due.append("evolution: " + ", ".join(e.id for e in evolution_options(state, data)))
        return due

    def choice_groups(self, state: GameState) -> list[dict[str, Any]]:
        """The same choices as `choices_due`, with display names, so the page can ask them all at once."""
        assert self.world.data is not None
        data = self.world.data
        groups: list[dict[str, Any]] = []

        def group(kind: str, title: str, options: list[tuple[str, str, str]], count: int = 1) -> None:
            items = [{"id": i, "name": n, "detail": d} for i, n, d in options]
            groups.append({"kind": kind, "title": title, "count": count, "options": items})

        if state.needs_class:
            group(
                "class",
                "Your class",
                [
                    (c.id, c.name, f"{c.primary.capitalize()} / {c.secondary.capitalize()}")
                    for c in data.classes
                ],
            )
            for option, cls in zip(groups[-1]["options"], data.classes, strict=True):
                option["blurb"], option["trait"] = cls.blurb, cls.trait
        trait = trait_of(state, data)
        if trait is not None and needs_attunement(state, data):
            group(
                "attunement",
                f"{trait.name}: your element",
                [(e, e.capitalize(), "Spells of it cost less and land surer") for e in trait.attunements],
            )
        if state.needs_profession:
            kinds = (
                ("Gathering", data.professions.gathering),
                ("Crafting", data.professions.crafting),
                ("Service", data.professions.service),
            )
            group("profession", "Your profession", [(p, p.capitalize(), k) for k, ps in kinds for p in ps])
        if state.free_points > 0:
            group(
                "point",
                "Place your free point",
                [(x, x.capitalize(), str(state.stats[x])) for x in STATS],
                state.free_points,
            )
        if state.skill_offers:
            names = {k.id: k for k in data.skills}
            group(
                "skill",
                "Your class offers a skill",
                [(o, names[o].name, names[o].rarity.capitalize()) for o in state.skill_offers[0]],
            )
        if state.needs_evolution:
            group(
                "evolution",
                "Choose your evolved class",
                [(e.id, e.name, "") for e in evolution_options(state, data)],
            )
        return groups

    def pretty(self, text: str) -> str:
        """Engine ids in Ledger lines become the names a player reads."""
        assert self.world.data is not None
        data = self.world.data
        names = {o.id: o.name for o in data.oaths}
        names |= {g.id: g.name for g in data.gods} | {c.id: c.name for c in data.classes}
        names |= {p.id: p.name for p in data.peoples} | {o.id: o.name for o in data.origins.origins}

        def swap(match: re.Match[str]) -> str:
            word = match.group(0)
            if word in names:
                return names[word]
            if word in STATS or word in data.affinities.basic or word in data.professions.all():
                return word.capitalize()
            return word.replace("_", " ") if "_" in word else word

        return re.sub(r"\b[a-z][a-z_]*\b", swap, text)

    def menu(self) -> None:
        state = self.state()
        out = self.console.print
        due = self.choices_due(state)
        if due:
            out("[bold]The player must choose first[/bold] (`session choose <kind> <id>`):")
            for line in due:
                out(f"  {escape(line)}")
        out(_status_line(state))
        if state.trial_ready:
            out("[bold]An Ascension Trial is ready.[/bold] The player may face it (`session trial`).")
        for number, action in enumerate(state.suggested, 1):
            odds = _odds_text(state, self.world, action)
            tag = f"[bold]\\[{action.tag.upper()}{odds}][/bold] " if action.tag else ""
            out(f"  {number}. {tag}{escape(action.label)}")
        offers = offer_choices(state, self.world)
        terms = offer_terms(state, self.world)
        for number, (choice_id, label) in enumerate(offers, len(state.suggested) + 1):
            out(f"  {number}. [bold]{label}[/bold] (`session choose offer {choice_id}`)")
            out(f"     [dim]{escape(terms[choice_id])}[/dim]")
        out("  [dim]Or type your own.[/dim]")

    def status(self) -> None:
        tid = self.db.latest_timeline()
        if tid is None or not self.db.load_state(tid).created:
            self.console.print("No character yet. See `session setup`, then `session create`.")
            return
        pending = self.load_pending()
        last = self.db.recent_turns(tid, 1)
        if last:
            self.console.print(escape(last[0][1]))
        if pending is not None:
            self.console.print(
                f"\n[bold]Turn {pending.turn} is in progress[/bold]: {escape(pending.player_input)}"
            )
            self.next_step(pending, self.replay(pending))
            return
        if not last:
            self.console.print("The opening has not been played. Run `session begin` with no text.")
            return
        self.menu()

    def choose(self, kind: str, choice: str) -> None:
        self.no_pending()
        sim = self.command_sim()
        handlers = {
            "class": choose_class,
            "attunement": choose_attunement,
            "profession": choose_profession,
            "point": allocate_point,
            "skill": pick_skill,
            "evolution": choose_evolution,
        }
        try:
            if kind == "offer":
                result = resolve_offer(sim, choice)
                if result["sworn"]:
                    sworn = f"I swear the {result['sworn']} Oath to {choice}"
                    text = f"[{sworn}. The Ledger opens. Narrate the aftermath.]"
                else:
                    text = "[I refuse both gods and stay Unwritten. Narrate the aftermath.]"
            elif kind in handlers:
                handlers[kind](sim, choice)
                text = ""
            else:
                raise SessionError(f"Unknown choice {kind}; use offer, {', '.join(handlers)}.")
        except Rejected as exc:
            raise SessionError(str(exc)) from exc
        self.commit_commands(sim)
        for line in ledger_lines(sim.events):
            self.console.print(f"  {line}")
        if kind == "offer" and sim.state.oaths:
            self.console.print(_sheet(sim.state, self.world))
        for line in self.choices_due(sim.state):
            self.console.print(f"Still to choose: {escape(line)}")
        if text:
            self.console.print(f'Next: `session begin "{text}"`')

    def trial(self) -> None:
        self.no_pending()
        sim = self.command_sim()
        try:
            result = attempt_trial(sim)
        except Rejected as exc:
            raise SessionError(str(exc)) from exc
        self.commit_commands(sim)  # Saved before any prose, so the roll stands.
        for line in ledger_lines(sim.events):
            self.console.print(f"  {line}")
        if result["result"] == "ascend":
            self.console.print(_sheet(sim.state, self.world))
        text = (
            f"[I face the Ascension Trial and the result is {result['result']}. Narrate it and what follows.]"
        )
        self.console.print(f'Next: `session begin "{text}"`')

    def screen(self) -> dict[str, Any]:
        """Everything the game page shows, as plain data (D-041). The page renders it; it decides nothing."""
        assert self.world.data is not None
        tid = self.db.latest_timeline()
        if tid is None or not self.db.load_state(tid).created:
            return {"created": False, "version": 0, "in_progress": False, "setup": self.setup_data()}
        state = self.db.load_state(tid)
        last = self.db.last_turn(tid)
        recent = self.db.recent_turns(tid, 1)
        logged = self.db.events(tid)
        events = [(e["type"], e["payload"]) for e in logged if e["turn"] >= last]
        prose = recent[0][1] if recent else ""
        plain = [Text.from_markup(line).plain for line in ledger_lines(events)]
        oaths = {o.id: o.name for o in self.world.data.oaths}
        current = self.world.data.class_of(state.class_id)
        terms = offer_terms(state, self.world)
        options = []
        for number, action in enumerate(state.suggested, 1):
            odds = _odds_text(state, self.world, action).strip()
            options.append(
                {
                    "n": number,
                    "label": action.label,
                    "tag": action.tag.upper() if action.tag else "",
                    "odds": odds,
                    "detail": Text.from_markup(_inspect(state, self.world, str(number))).plain,
                }
            )
        offers = [
            {"n": n, "id": cid, "label": label, "terms": terms[cid]}
            for n, (cid, label) in enumerate(offer_choices(state, self.world), len(state.suggested) + 1)
        ]
        data = self.world.data
        skills = {k.id: k for k in data.skills}
        gods = {g.id: g.name for g in data.gods}
        origin = next((o for o in data.origins.origins if o.id == state.origin), None)
        people = next((p for p in data.peoples if p.id == state.people), None)
        clocks = []
        for clock in data.clocks:
            value = clock_value(state, data, clock.id)
            if value > clock.start:  # The same rule as the narrator's brief: only clocks that have moved.
                clocks.append(
                    {
                        "name": clock.name,
                        "value": value,
                        "segments": clock.segments,
                        "filled": clock.filled if value >= clock.segments else "",
                    }
                )
        return {
            "created": True,
            "people_name": people.name if people else state.people,
            "origin_name": origin.name if origin else state.origin,
            "flaw": state.flaw,
            "debt": state.debt,
            "class_catalogue": [
                {
                    "name": c.name,
                    "stats": f"{c.primary.capitalize()} / {c.secondary.capitalize()}",
                    "blurb": c.blurb,
                    "trait": c.trait,
                    "current": c.id == state.class_id,
                }
                for c in data.classes
            ],
            "class_stats": f"{current.primary.capitalize()} / {current.secondary.capitalize()}"
            if current
            else "",
            "skill_list": [
                {
                    "name": skills[k].name if k in skills else k.replace("_", " ").capitalize(),
                    "rank": rank,
                    "rarity": state.skill_rarity.get(k, skills[k].rarity if k in skills else ""),
                    "affinity": skills[k].affinity or "" if k in skills else "",
                }
                for k, rank in state.skills.items()
            ],
            "oath_list": [
                {"name": o.name, "god": gods.get(o.god, o.god), "gift": o.perk, "burden": o.burden}
                for o in data.oaths
                if o.id in state.oaths
            ],
            "shards": [
                f"{s.target} {'fragment' if s.fragment else s.kind} ({s.rarity})" for s in state.shards
            ],
            "rumours": list(state.rumours),
            "clocks": clocks,
            "timeline": tid[:8],
            "turn": last,
            "version": len(logged),  # Grows with every saved change, so the page knows its move was taken.
            "in_progress": self.pending_path.exists(),
            "date": format_date(date_of(state.day)),
            "name": state.name,
            "people": state.people,
            "age": state.age,
            "class": current.name if current else "",
            "profession": (state.profession or "").capitalize(),
            "tier": state.tier,
            "level": state.level,
            "xp": state.xp,
            "xp_next": xp_to_next(state.level) if state.level else 0,
            "hp": state.hp,
            "max_hp": state.max_hp,
            "max_mana": state.max_mana,
            "max_stamina": state.max_stamina,
            "downed": state.downed,
            "coin": state.coin,
            "stats": {s: state.stats[s] for s in STATS},
            "affinities": {a.capitalize(): r for a, r in state.affinities.items()},
            "skills": state.skills,
            "oaths": [oaths[o] for o in state.oaths],
            "standing": {self.pretty(e).capitalize(): v for e, v in state.standing.items()},
            "titles": list(state.titles),
            "injuries": [f"{i.stat} -{i.amount}" for i in state.injuries],
            "hooks": [h.description for h in state.hooks if not h.resolved],
            "prose": [line for line in prose.split("\n") if line.strip()] if prose else [],
            "ledger": [self.pretty(line) for line in plain if line not in prose],
            "options": options,
            "offers": offers,
            "choices_due": self.choices_due(state),
            "choice_groups": self.choice_groups(state),
            "trial_ready": state.trial_ready,
        }

    def setup_data(self) -> dict[str, Any]:
        """The choices for a new character, for the game page's creation form."""
        assert self.world.data is not None
        data = self.world.data
        blank = Simulation(GameState(), RngStreams.from_seed(1), self.rules, 0)
        return {
            "peoples": [
                {
                    "id": p.id,
                    "name": p.name,
                    "stat": p.stat,
                    "affinities": list(innate_affinity_options(blank, p.id)),
                }
                for p in data.peoples
            ],
            "origins": [
                {
                    "id": o.id,
                    "name": o.name,
                    "text": f"{o.stat.capitalize()} +2, {o.skill.capitalize()} 1. {o.complication}.",
                }
                for o in data.origins.origins
            ],
            "stats": list(STATS),
            "stat_array": list(data.origins.stat_array),
            "flaws": list(data.origins.flaws),
        }

    # A new character.

    def setup(self) -> None:
        assert self.world.data is not None
        data = self.world.data
        out = self.console.print
        out("[bold]New character[/bold]: ask the player, then run `session create`.")
        for p in data.peoples:
            out(f"  people {p.id}: {p.name}, stat {p.stat}")
        for o in data.origins.origins:
            out(f"  origin {o.id}: {o.name}: {o.stat} +2, {o.skill} 1. {o.complication}.")
        out(
            f"  stats, strongest first, get {', '.join(map(str, data.origins.stat_array))}: "
            + ", ".join(STATS)
        )
        out(f"  flaws: {'; '.join(data.origins.flaws)} (or the player's own)")
        out("  age 16 to 30; a debt: a sum, a favour or a name owed, and to whom")
        out("  People with a choice of affinity or stat: `session create` lists them if needed.")

    def create(self, args: argparse.Namespace) -> None:
        tid = self.db.latest_timeline()
        if tid is not None and self.db.load_state(tid).created and not args.fresh:
            raise SessionError("A character exists. Pass --fresh to start a new timeline beside it.")
        if tid is None or args.fresh:
            tid = _create_timeline(self.db, self.world, self.config, args.seed, self.console)
        rng = RngStreams.from_state(self.db.rng_state(tid))
        sim = Simulation(self.db.load_state(tid), rng, self.rules, 0)
        parts = args.stats.lower().replace(",", " ").split()
        order = [next((s for s in STATS if s.startswith(p)), "") for p in parts]
        if sorted(order) != sorted(STATS):
            raise SessionError(f"--stats must name each of {', '.join(STATS)} once.")
        assert self.world.data is not None
        stats = dict(zip(order, self.world.data.origins.stat_array, strict=True))
        affinities = innate_affinity_options(sim, args.people)
        if args.affinity is None and len(affinities) > 1:
            raise SessionError(f"Pass --affinity, one of: {', '.join(affinities)}.")
        choices = CharacterChoices(
            name=args.name,
            people=args.people,
            origin=args.origin,
            age=args.age,
            flaw=args.flaw or self.world.data.origins.flaws[0],
            debt=args.debt or "A favour owed",
            stats=stats,
            people_stat=args.people_stat,
            innate_affinity=args.affinity or affinities[0],
        )
        try:
            create_character(sim, choices)
        except (Rejected, ValueError, KeyError) as exc:
            raise SessionError(f"Character not created: {exc}") from exc
        self.db.commit_events(tid, 0, sim.events, rng.state())
        self.console.print(_sheet(sim.state, self.world))
        self.console.print("Next: `session begin` with no text plays the opening.")

    # The canon prefix and tool fields, read once per session.

    def prompt(self) -> None:
        system, _ = assemble(self.state(), self.world, [], "", self.config.violence)
        for block in system:
            self.console.print(escape(block["text"]), soft_wrap=True)

    def tools(self) -> None:
        pending = self.load_pending()
        names = self.offered(pending, self.replay(pending)) if pending else ("request_check", *_SCRIBE_TOOLS)
        for name in names:
            self.console.print(escape(json.dumps(tool_definition(name))), soft_wrap=True)


def export_db(db_path: Path, out: Path) -> None:
    """A text dump of the whole save, so git can store and diff it (D-041)."""
    conn = sqlite3.connect(db_path)
    try:
        out.write_text("\n".join(conn.iterdump()) + "\n", encoding="utf-8")
    finally:
        conn.close()


def import_db(dump: Path, db_path: Path) -> Path | None:
    """Rebuild the save from a dump. An existing save is moved aside first, never overwritten (GAME-05)."""
    backup = None
    if db_path.exists():
        backup = db_path.with_name(f"{db_path.name}.{time.strftime('%Y%m%d-%H%M%S')}.bak")
        shutil.move(db_path, backup)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(dump.read_text(encoding="utf-8"))
    finally:
        conn.close()
    return backup


def add_parser(sub: Any) -> None:
    session = sub.add_parser("session", help="play with Claude Code as the narrator (D-041)")
    session.add_argument("--db", help="database path (default: data/pantheon.db)")
    session.add_argument("--config", help="config file (default: config.toml)")
    steps = session.add_subparsers(dest="step", required=True)
    steps.add_parser("start", help="enter play mode: the play guard turns on")
    steps.add_parser("stop", help="leave play mode")
    steps.add_parser("status", help="the last scene and what to do next")
    steps.add_parser("prompt", help="the narrator's instructions and public canon, once per session")
    steps.add_parser("tools", help="the fields of the tools allowed now")
    steps.add_parser("setup", help="the choices for a new character")
    create = steps.add_parser("create", help="create the character")
    create.add_argument("--name", required=True)
    create.add_argument("--people", required=True)
    create.add_argument("--origin", required=True)
    create.add_argument("--stats", default="a p v i r", help="the five stats, strongest first")
    create.add_argument("--age", type=int, default=22)
    create.add_argument("--flaw", default="")
    create.add_argument("--debt", default="")
    create.add_argument("--people-stat", dest="people_stat")
    create.add_argument("--affinity")
    create.add_argument("--seed", type=int, default=0)
    create.add_argument("--fresh", action="store_true", help="a new timeline beside the existing one")
    begin = steps.add_parser("begin", help="start a turn with what the player does")
    begin.add_argument("text", nargs="?", default="")
    begin.add_argument("--option", type=int, help="the number of a suggested action")
    tool = steps.add_parser("tool", help="one narrator tool call")
    tool.add_argument("name")
    tool.add_argument("args", nargs="?", default="{}")
    narrate = steps.add_parser("narrate", help="submit the prose, from a file")
    narrate.add_argument("file")
    steps.add_parser("commit", help="save the turn and show the options")
    steps.add_parser("abandon", help="drop the turn in progress")
    choose = steps.add_parser(
        "choose", help="a player choice: offer, class, profession, point, skill, evolution"
    )
    choose.add_argument("kind")
    choose.add_argument("choice")
    steps.add_parser("trial", help="face the Ascension Trial")
    steps.add_parser("sheet", help="the character sheet")
    steps.add_parser("hooks", help="consequences that may come back")
    screen = steps.add_parser("screen", help="write the game page's data as JSON")
    screen.add_argument("file")
    inspect = steps.add_parser("inspect", help="one option's odds and stakes")
    inspect.add_argument("number")
    export = steps.add_parser("export", help="write the save as text")
    export.add_argument("file")
    load = steps.add_parser("import", help="replace the save from a text dump; the old one is kept as .bak")
    load.add_argument("file")


def run(args: argparse.Namespace, console: Console) -> int:
    config = load_config(Path(args.config) if args.config else None)
    db_path = Path(args.db) if args.db else config.db_path
    try:
        if args.step == "export":
            export_db(db_path, Path(args.file))
            console.print(f"Saved the game as text to {args.file}.")
            return 0
        if args.step == "import":
            backup = import_db(Path(args.file), db_path)
            console.print(
                f"Loaded the save from {args.file}." + (f" The old one is {backup}." if backup else "")
            )
            return 0
        if args.step in ("start", "stop"):
            marker = db_path.parent / PLAYING
            if args.step == "start":
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.touch()
                console.print("Play mode on: only public files and `pantheon session` until `session stop`.")
            else:
                marker.unlink(missing_ok=True)
                console.print("Play mode off.")
            if args.step == "stop":
                return 0
        world = load_world(config.world_dir)
        if world.data is None:
            raise SessionError("world/data/ is missing.")
        with Database.open(db_path) as db:
            session = Session(db, db_path, world, config, console)
            _dispatch(session, args)
    except SessionError as exc:
        console.print(f"[red]{escape(str(exc))}[/red]")
        return 1
    return 0


def _dispatch(session: Session, args: argparse.Namespace) -> None:
    match args.step:
        case "start" | "status":
            session.status()
        case "prompt":
            session.prompt()
        case "tools":
            session.tools()
        case "setup":
            session.setup()
        case "create":
            session.create(args)
        case "begin":
            session.begin(args.text, args.option)
        case "tool":
            session.tool(args.name, args.args)
        case "narrate":
            session.narrate(Path(args.file))
        case "commit":
            session.commit()
        case "abandon":
            session.abandon()
        case "choose":
            session.choose(args.kind, args.choice)
        case "trial":
            session.trial()
        case "sheet":
            session.console.print(_sheet(session.state(), session.world))
        case "hooks":
            for hook in (h for h in session.state().hooks if not h.resolved):
                session.console.print(
                    f"  {hook.id}. {escape(hook.description)} (due {escape(hook.due_condition)})"
                )
        case "screen":
            Path(args.file).write_text(json.dumps(session.screen(), indent=1), encoding="utf-8")
            session.console.print(f"Screen written to {args.file}.")
        case "inspect":
            session.console.print(_inspect(session.state(), session.world, args.number))
