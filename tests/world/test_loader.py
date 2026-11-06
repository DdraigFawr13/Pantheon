"""WLD-01 and WLD-04: every canon file loads and validates; a malformed file fails."""

from pathlib import Path

import pytest

from pantheon.world.loader import CanonError, World, load_world

ROOT = Path(__file__).resolve().parents[2]
WORLD = ROOT / "world"
BAD = ROOT / "tests" / "fixtures" / "world_bad"


def test_wld01_every_world_file_loads(world: World) -> None:
    assert len(world.lore) >= 15
    assert len({e.id for e in world.lore}) == len(world.lore)


def test_wld01_secret_and_sealed_entries_have_gates(world: World) -> None:
    hidden = [e for e in world.lore if e.visibility == "secret"]
    assert hidden
    assert all(e.gate is not None for e in hidden)
    sealed = [e for e in world.lore if e.path.parts[-2] == "sealed"]
    assert sealed
    assert all(e.visibility == "secret" for e in sealed)


def test_wld01_public_entries_have_no_gate(world: World) -> None:
    assert all(e.reveal_gate is None for e in world.lore if e.visibility == "public")


EXPECTED = {
    "bad_gate.md": "reveal_gate does not parse",
    "bad_visibility.md": "visibility",
    "missing_id.md": "id",
    "no_frontmatter.md": "missing YAML frontmatter",
    "secret_without_gate.md": "secret entries need a reveal_gate",
}


def test_wld01_every_bad_fixture_has_an_expected_message() -> None:
    assert sorted(EXPECTED) == sorted(p.name for p in BAD.glob("*.md"))


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_wld01_malformed_files_fail(name: str, tmp_path: Path) -> None:
    (tmp_path / name).write_text((BAD / name).read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(CanonError, match=EXPECTED[name]):
        load_world(tmp_path)
