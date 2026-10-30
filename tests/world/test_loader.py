"""WLD-01 and WLD-04: every canon file loads and validates; a malformed file fails."""

from pathlib import Path

import pytest

from pantheon.world.loader import CanonError, load_world

ROOT = Path(__file__).resolve().parents[2]
WORLD = ROOT / "world"
BAD = ROOT / "tests" / "fixtures" / "world_bad"


def test_wld01_every_world_file_loads() -> None:
    world = load_world(WORLD)
    assert len(world.lore) >= 15
    assert len({e.id for e in world.lore}) == len(world.lore)


def test_wld01_secret_and_sealed_entries_have_gates() -> None:
    world = load_world(WORLD)
    hidden = [e for e in world.lore if e.visibility == "secret"]
    assert hidden
    assert all(e.gate is not None for e in hidden)
    sealed = [e for e in world.lore if e.path.parts[-2] == "sealed"]
    assert sealed
    assert all(e.visibility == "secret" for e in sealed)


def test_wld01_public_entries_have_no_gate() -> None:
    assert all(e.reveal_gate is None for e in load_world(WORLD).lore if e.visibility == "public")


@pytest.mark.parametrize("name", sorted(p.name for p in BAD.glob("*.md")))
def test_wld01_malformed_files_fail(name: str, tmp_path: Path) -> None:
    (tmp_path / name).write_text((BAD / name).read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(CanonError):
        load_world(tmp_path)
