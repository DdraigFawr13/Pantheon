"""Build the prompt in fixed layers (NAR-01). Thin slice: no chronicle yet; public lore only (NAR-02)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pantheon.engine.calendar import clock_value, date_of
from pantheon.engine.combat import intent_label
from pantheon.engine.state import GameState, xp_to_next
from pantheon.world.loader import World

_CANON_CORE = ("overview", "power_tiers", "pantheon")
_LORE = ("peoples", "geography", "factions", "economy")
_OPENING_LORE = "protagonist_seed"
_PROMPT = Path(__file__).resolve().parents[3] / "prompts" / "narrator.md"
_MAX_HOOKS_SHOWN = 12
# Small local models follow the end of the prompt best. Not stored with the turn (first live playtest).
_REMINDER = (
    "[Narrator: write the scene once: 200 to 400 words, third person, past tense, close on the character, in "
    "plain everyday prose. The character reasons on the page, using stats by name, with a dry italic thought "
    "now and then. Numbers only from the sheet or this turn's results; never state dice. Invent no "
    "belongings and no injury the result did not give. Move the scene forward with something new, and never "
    "reuse an image or phrase from earlier turns. Weigh what could be done next and what each choice would "
    "cost, then end on a hook. No lists or headings. Never decide the player's next action.]"
)


def state_view(state: GameState) -> dict[str, Any]:
    """The curated sheet the narrator sees (D-022): no roll logs and nothing gated."""
    return {
        "date": date_of(state.day).view(),
        "name": state.name,
        "people": state.people,
        "origin": state.origin,
        "age": state.age,
        "flaw": state.flaw,
        "tier": state.tier,
        "level": state.level,
        "class": state.class_id or "(none yet)",
        "profession": state.profession or "(none yet)",
        "stats": state.stats,
        "hp": state.hp,
        "max_hp": state.max_hp,
        "mana": state.mana,
        "max_mana": state.max_mana,
        "stamina": state.stamina,
        "max_stamina": state.max_stamina,
        "xp": state.xp,
        "xp_to_next": xp_to_next(state.level) if state.level else 0,
        "downed": state.downed,
        "affinities": state.affinities,
        "skills": state.skills,
        "oaths": state.oaths,
        "standing": state.standing,
        "story_flags": {k: v for k, v in state.flags.items() if k.startswith("story.")},
    }


def _due_material(state: GameState, world: World) -> str:
    assert world.data is not None
    lines = []
    if not state.offer_resolved:
        gods = {g.id: g for g in world.data.gods}
        oaths = {o.id: o for o in world.data.oaths}
        offers = []
        for god_id in state.opening_gods:
            oath = oaths[gods[god_id].first_oath]
            offers.append(
                f"{gods[god_id].name} offers the {oath.name}. Gift: {oath.perk}. Burden: {oath.burden}"
            )
        lines.append(
            "The Dual Offer is unresolved. "
            + "; ".join(offers)
            + ". The voices speak in the dark and answer "
            "questions. The player has not chosen and the Ledger stays closed until they do. The game gives "
            "the player a menu for swearing or refusing, so never present that choice in prose or in "
            "suggest_actions; suggest questions, bargains and reactions instead."
        )
    if state.fight is not None:
        lines.append(f"A fight is on, exchange {state.fight.exchange}. Each foe's shown intent:")
        lines += [
            f"- {f.id}: {f.name}, Tier {f.tier}, {f.threat}, shows {intent_label(world.data, f.intent)}."
            for f in state.fight.standing
        ]
    open_hooks = [h for h in state.hooks if not h.resolved]
    lines += [
        f"- Hook {h.id} (turn {h.turn}): {h.description}. Due: {h.due_condition}."
        for h in open_hooks[-_MAX_HOOKS_SHOWN:]
    ]
    for clock in world.data.clocks:
        value = clock_value(state, world.data, clock.id)
        if value >= clock.segments:
            lines.append(f"- {clock.name} has filled: {clock.filled}")
        elif value > clock.start:
            lines.append(f"- {clock.name} has moved: {value} of {clock.segments} segments.")
    return "\n".join(lines) or "(nothing due)"


def history_window(last_turn: int, size: int) -> int:
    """How many past turns to send. It grows, then resets, so the model's cache survives most turns."""
    return size + last_turn % size


def assemble(
    state: GameState,
    world: World,
    recent: list[tuple[str, str]],
    player_input: str,
    violence: str = "moderate",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (system blocks, messages). The first block is the stable, cached canon prefix (OPS-04)."""
    template = _PROMPT.read_text(encoding="utf-8").split("\n---\n", 1)[1].strip()
    template = template.replace("`config.gameplay.violence`", f'the "{violence}" setting')
    prefix, rest = template.split("{{canon_core}}")
    canon = "\n\n".join(world.by_id(entry).body for entry in _CANON_CORE)
    lore_ids = ((_OPENING_LORE,) if not state.offer_resolved else ()) + _LORE
    lore = "\n\n".join(world.by_id(entry).body for entry in lore_ids)
    rest = rest.replace("{{chronicle}}", "(not kept in this build; recent turns follow as messages)").replace(
        "{{retrieved_lore}}", lore
    )
    system = [
        {"type": "text", "text": prefix + canon, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": rest.strip()},
    ]
    messages: list[dict[str, Any]] = []
    for said, narration in recent:
        messages += [{"role": "user", "content": said}, {"role": "assistant", "content": narration}]
    # Sheet first and instructions last, so every call this turn reuses the model's cache up to the steps.
    sheet = json.dumps(state_view(state), separators=(",", ":"))
    due = _due_material(state, world)
    latest = f"[Character sheet: {sheet}]\n[Due: {due}]\n\nThe player: {player_input}\n\n{_REMINDER}"
    messages.append({"role": "user", "content": latest})
    return system, messages
