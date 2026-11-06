"""Shared test setup: pinned Hypothesis profile, one loaded world, cached world loads."""

from collections.abc import Callable
from pathlib import Path

import pytest
from hypothesis import settings

from pantheon.world import loader
from pantheon.world.loader import World

settings.register_profile("pantheon", derandomize=True, deadline=None, database=None)
settings.load_profile("pantheon")

WORLD_DIR = Path(__file__).resolve().parents[1] / "world"


WORLD = loader.load_world(WORLD_DIR)  # loaded and validated once per test session


@pytest.fixture(scope="session")
def world() -> World:
    """The canon world, shared by every test."""
    return WORLD


@pytest.fixture(autouse=True)
def _cached_load_world(monkeypatch: pytest.MonkeyPatch) -> None:
    """Memoise `load_world` where the CLI imports it (F22); production code is untouched."""
    from pantheon.ui.cli import app, session

    real: Callable[[Path], World] = loader.load_world
    cache = _WORLD_CACHE

    def cached(path: Path) -> World:
        key = Path(path).resolve()
        if key not in cache:
            cache[key] = real(path)
        return cache[key]

    monkeypatch.setattr(session, "load_world", cached)
    monkeypatch.setattr(app, "load_world", cached)


_WORLD_CACHE: dict[Path, World] = {WORLD_DIR.resolve(): WORLD}
