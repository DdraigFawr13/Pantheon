"""The opening scene's two gods, drawn from the timeline seed (D-017)."""

from __future__ import annotations

from pantheon.engine.rng import RngStreams


def draw_opening_gods(
    rng: RngStreams, god_ids: tuple[str, ...], fixed: tuple[str, str] | None = None
) -> tuple[str, ...]:
    """Return the two gods who speak in the opening. `fixed` (from config) overrides the draw for tests."""
    if fixed is not None:
        unknown = [g for g in fixed if g not in god_ids]
        if unknown or fixed[0] == fixed[1]:
            raise ValueError(f"opening_gods must name two different known gods, got {fixed}")
        return fixed
    return rng.choose_distinct("opening", tuple(sorted(god_ids)), 2)
