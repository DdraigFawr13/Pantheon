"""ENG-03 and D-022: seeded, named RNG streams; D-017: the opening god draw."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pantheon.engine.opening import draw_opening_gods
from pantheon.engine.rng import RngStreams

GODS = ("veshra", "kaul", "ysmere", "maru_ghen", "ilvane", "drovash", "hurrow")


def test_eng03_same_seed_gives_same_sequence() -> None:
    a, b = RngStreams.from_seed(42), RngStreams.from_seed(42)
    assert [a.roll("checks", 100) for _ in range(20)] == [b.roll("checks", 100) for _ in range(20)]


def test_d022_streams_are_independent() -> None:
    plain, busy = RngStreams.from_seed(7), RngStreams.from_seed(7)
    for _ in range(50):
        busy.roll("loot", 100)
    assert [plain.roll("checks", 100) for _ in range(10)] == [busy.roll("checks", 100) for _ in range(10)]


def test_eng08_state_round_trips_mid_sequence() -> None:
    a = RngStreams.from_seed(99)
    for _ in range(5):
        a.roll("checks", 100)
    b = RngStreams.from_state(a.state())
    assert [a.roll("checks", 100) for _ in range(10)] == [b.roll("checks", 100) for _ in range(10)]


def test_roll_bounds() -> None:
    rng = RngStreams.from_seed(1)
    assert {rng.roll("checks", 6) for _ in range(500)} == {1, 2, 3, 4, 5, 6}


def test_unknown_stream_is_rejected() -> None:
    rng = RngStreams.from_seed(1)
    with pytest.raises(KeyError):
        rng.roll("nonsense", 6)


@given(st.integers(min_value=1, max_value=2**63 - 1))
def test_d017_opening_draw_is_two_distinct_gods_and_deterministic(seed: int) -> None:
    first = draw_opening_gods(RngStreams.from_seed(seed), GODS)
    again = draw_opening_gods(RngStreams.from_seed(seed), GODS)
    assert first == again
    assert len(set(first)) == 2
    assert set(first) <= set(GODS)


def test_d017_draw_covers_many_pairs() -> None:
    pairs = {frozenset(draw_opening_gods(RngStreams.from_seed(s), GODS)) for s in range(1, 400)}
    assert len(pairs) == 21


def test_d017_fixed_pair_from_config() -> None:
    assert draw_opening_gods(RngStreams.from_seed(5), GODS, fixed=("kaul", "hurrow")) == ("kaul", "hurrow")


def test_roll_rejects_zero_sides() -> None:
    with pytest.raises(ValueError):
        RngStreams.from_seed(1).roll("checks", 0)


@pytest.mark.parametrize("bad", [("kaul", "kaul"), ("kaul", "nobody")])
def test_d017_fixed_pair_must_be_two_known_gods(bad: tuple[str, str]) -> None:
    with pytest.raises(ValueError):
        draw_opening_gods(RngStreams.from_seed(5), GODS, fixed=bad)
