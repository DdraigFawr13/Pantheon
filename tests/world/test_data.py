"""GAME-04: data tables load, cross-reference, and agree with the prose rulebook."""

import re
from pathlib import Path

import pytest
import yaml

from pantheon.world.loader import CanonError, World, load_data

ROOT = Path(__file__).resolve().parents[2]
WORLD = ROOT / "world"


def _text(name: str) -> str:
    return (WORLD / name).read_text(encoding="utf-8")


def test_data_tables_load(world: World) -> None:
    data = world.data
    assert data is not None
    assert len(data.gods) == 7
    assert len(data.affinities.basic) == 15
    assert len(data.affinities.rare) + data.affinities.sealed_rare_slots == 5
    assert len(data.classes) == 25  # D-042
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
    with pytest.raises(CanonError, match="unknown affinity fate"):
        load_data(tmp_path)


# The nine fight traits the engine runs (D-045). Their numbers live in combat.yaml; the canon trait text in
# classes.yaml must say the same numbers (design audit 2026-11-06 F13). Hexer's damage cut is an assumed extra.
_TRAIT_NUMBER = re.compile(r"\d+")


def _numbers(value: object) -> set[int]:
    if isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {abs(value)}
    if isinstance(value, dict):
        return set().union(*(_numbers(v) for v in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(_numbers(v) for v in value)) if value else set()
    return set()


def test_eng13_trait_text_numbers_match_combat_data() -> None:
    classes = {c["id"]: c["trait"] for c in yaml.safe_load(_text("data/classes.yaml"))}
    traits = yaml.safe_load(_text("data/combat.yaml"))["traits"]
    mismatched = {}
    for class_id, entry in traits.items():
        assert classes[class_id].startswith(entry["name"] + ":"), class_id
        said = {int(n) for n in _TRAIT_NUMBER.findall(classes[class_id])}
        if not said <= _numbers(entry):
            mismatched[class_id] = sorted(said - _numbers(entry))
    assert mismatched == {}


_COIN_CP = {"cp": 1, "sp": 12, "gp": 240}


def _price_list() -> dict[str, int]:
    """world/economy.md's price table: the home of every price (design audit 2026-11-06 F16)."""
    prices = {}
    for name, price in re.findall(r"^\| ([^|]+?) \| (\d+ (?:cp|sp|gp)) \|$", _text("economy.md"), re.M):
        amount, coin = price.split()
        key = re.sub(r"[^a-z0-9]+", " ", re.sub(r"\(common\)", "", name.lower())).strip()
        prices[key] = int(amount) * _COIN_CP[coin]
    return prices


def test_eng09_item_prices_and_tonic_heal_match_their_homes() -> None:
    prices = _price_list()
    items = yaml.safe_load(_text("data/items.yaml"))
    wrong = {}
    for item in items:
        key = re.sub(r"[^a-z0-9]+", " ", item["name"].lower()).strip()
        if prices.get(key) != item["value_cp"]:
            wrong[item["id"]] = (item["value_cp"], prices.get(key))
    assert wrong == {}
    tonic = next(i for i in items if i["id"] == "healing_tonic")
    assert tonic["heal_percent"] == yaml.safe_load(_text("data/rewards.yaml"))["heal_percent"]["aid"]
