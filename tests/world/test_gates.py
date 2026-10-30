"""Reveal-gate grammar (architecture section 7): comparisons, and/or/not, parentheses, paths. No eval."""

import pytest

from pantheon.world.gates import GateError, evaluate, parse

STATE = {
    "tier": 3,
    "standing": {"ilvane": 45},
    "flags": {"rifts_closed": 1, "met": True, "unwritten_path": False},
}


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("tier >= 3", True),
        ("tier > 3", False),
        ("tier >= 3 and standing.ilvane >= 40 and flags.rifts_closed >= 1", True),
        ("flags.met", True),
        ("flags.unwritten_path", False),
        ("flags.missing", False),
        ("not flags.missing", True),
        ("flags.met and (tier >= 5 or flags.unwritten_path)", False),
        ("flags.met and (tier >= 2 or flags.unwritten_path)", True),
        ("standing.missing >= 0", False),
        ("tier == 3", True),
        ("tier != 3", False),
        ('location.region == "ford_reaches"', False),
    ],
)
def test_gate_evaluation(expr: str, expected: bool) -> None:
    assert evaluate(parse(expr), STATE) is expected


@pytest.mark.parametrize(
    "expr",
    ["__import__('os')", "tier >=", "tier >= 3 and", "(tier >= 3", "tier >= 3)", "tier; drop", "a.b()", ""],
)
def test_gate_rejects_bad_input(expr: str) -> None:
    with pytest.raises(GateError):
        parse(expr)


def test_gate_paths_lists_every_path() -> None:
    assert parse("flags.a and (tier >= 2 or not standing.x > 1)").paths() == {"flags.a", "tier", "standing.x"}
