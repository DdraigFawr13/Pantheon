"""GAME-04: data tables load, cross-reference, and agree with the prose rulebook."""

from pathlib import Path

import pytest

from pantheon.world.loader import CanonError, load_data, load_world

ROOT = Path(__file__).resolve().parents[2]
WORLD = ROOT / "world"


def _text(name: str) -> str:
    return (WORLD / name).read_text(encoding="utf-8")


def test_data_tables_load() -> None:
    data = load_world(WORLD).data
    assert data is not None
    assert len(data.gods) == 7
    assert len(data.affinities.basic) == 15
    assert len(data.affinities.rare) + data.affinities.sealed_rare_slots == 5
    assert len(data.classes) == 8
    assert len(data.peoples) == 5
    assert len(data.professions.all()) == 15


def test_data_names_match_the_prose() -> None:
    data = load_data(WORLD / "data")
    rules, pantheon, peoples = _text("power_tiers.md"), _text("pantheon.md"), _text("peoples.md")
    missing = [a for a in data.affinities.all_named() if a.capitalize() not in rules]
    missing += [c.name for c in data.classes if c.name not in rules]
    missing += [o.name for o in data.oaths if o.name not in rules]
    missing += [p.capitalize() for p in data.professions.all() if p.capitalize() not in rules]
    missing += [g.name for g in data.gods if g.name not in pantheon]
    missing += [p.name for p in data.peoples if p.name not in peoples]
    assert missing == []


def test_broken_reference_fails(tmp_path: Path) -> None:
    for f in (WORLD / "data").glob("*.yaml"):
        (tmp_path / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    oaths = tmp_path / "oaths.yaml"
    oaths.write_text(
        oaths.read_text(encoding="utf-8").replace("affinity: mind", "affinity: fate"), encoding="utf-8"
    )
    with pytest.raises(CanonError):
        load_data(tmp_path)
