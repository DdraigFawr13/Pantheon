"""Seeded, named random streams (ENG-03, D-022).

Each stream has its own generator, so rolling loot never shifts the next check.
Stream state serialises to plain JSON types so forks can restore it (ENG-08).
"""

from __future__ import annotations

import random
from typing import Any

STREAMS: tuple[str, ...] = ("checks", "combat", "loot", "opening", "rival", "world")

type StreamState = dict[str, list[Any]]


class RngStreams:
    def __init__(self, generators: dict[str, random.Random]) -> None:
        self._generators = generators

    @classmethod
    def from_seed(cls, seed: int) -> RngStreams:
        return cls({name: random.Random(f"pantheon:{seed}:{name}") for name in STREAMS})

    @classmethod
    def from_state(cls, state: StreamState) -> RngStreams:
        generators = {}
        for name in STREAMS:
            gen = random.Random()
            version, internal, gauss = state[name]
            gen.setstate((version, tuple(internal), gauss))
            generators[name] = gen
        return cls(generators)

    def state(self) -> StreamState:
        out: StreamState = {}
        for name, gen in self._generators.items():
            version, internal, gauss = gen.getstate()
            out[name] = [version, list(internal), gauss]
        return out

    def roll(self, stream: str, sides: int) -> int:
        """Return an integer from 1 to `sides` inclusive from the named stream."""
        if sides < 1:
            raise ValueError("sides must be at least 1")
        return self._generators[stream].randint(1, sides)

    def choose_distinct(self, stream: str, options: tuple[str, ...], count: int) -> tuple[str, ...]:
        return tuple(self._generators[stream].sample(options, count))
