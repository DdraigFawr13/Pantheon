"""ENG-03, ENG-04 and ENG-05: d100 checks, rules from `world/power_tiers.md` Checks; assumptions in D-028."""

import dataclasses
import hashlib
import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pantheon.engine.checks import (
    Approach,
    CheckRequest,
    Difficulty,
    Outcome,
    OvercomeClaim,
    OvercomeKind,
    base_chance,
    outcome_for,
    par,
    resolve_check,
    stat_edge,
)
from pantheon.engine.rng import RngStreams


class FixedRolls(RngStreams):
    """Returns the given rolls in order; fails the test if the engine rolls more often than expected."""

    def __init__(self, *rolls: int) -> None:
        super().__init__({})
        self.rolls = list(rolls)
        self.calls: list[tuple[str, int]] = []

    def roll(self, stream: str, sides: int) -> int:
        self.calls.append((stream, sides))
        return self.rolls.pop(0)


def request(**overrides: object) -> CheckRequest:
    """Tier 1 actor at par (stat 35, edge 0) against Tier 1, no skill, Routine: chance 60."""
    fields: dict[str, object] = {
        "difficulty": Difficulty.ROUTINE,
        "stat": 35,
        "skill_rank": 0,
        "actor_tier": 1,
        "challenge_tier": 1,
        "approach": Approach.OTHER,
        "overcome": None,
    }
    return CheckRequest(**(fields | overrides))  # type: ignore[arg-type]


@pytest.mark.parametrize(("tier", "expected"), [(0, 20), (1, 35), (2, 50), (7, 125), (8, 140)])
def test_eng04_par(tier: int, expected: int) -> None:
    assert par(tier) == expected


@pytest.mark.parametrize(
    ("stat", "tier", "expected"),
    [
        (35, 1, 0),
        (39, 1, 0),
        (40, 1, 1),
        (45, 1, 2),
        (34, 1, -1),
        (30, 1, -1),
        (29, 1, -2),
        (24, 1, -3),
        (0, 0, -4),
    ],
)
def test_eng04_stat_edge_floors_toward_negative_infinity(stat: int, tier: int, expected: int) -> None:
    assert stat_edge(stat, tier) == expected


@pytest.mark.parametrize(
    ("difficulty", "expected"),
    [(Difficulty.ROUTINE, 60), (Difficulty.HARD, 40), (Difficulty.SEVERE, 20), (Difficulty.HEROIC, 0)],
)
def test_eng04_difficulty_values(difficulty: Difficulty, expected: int) -> None:
    assert base_chance(difficulty, stat=35, skill_rank=0, actor_tier=1, tier_gap=0) == expected


def test_eng04_chance_adds_every_term() -> None:
    # 40 (Hard) + 2 (stat 45 at Tier 1) + 5 * 2 (rank) + 20 * 1 (gap) = 72
    assert base_chance(Difficulty.HARD, stat=45, skill_rank=2, actor_tier=1, tier_gap=1) == 72


# Band edges at chance 60, with rolls outside the 01-05 and 96-00 ranges.
@pytest.mark.parametrize(
    ("chance", "roll", "expected"),
    [
        (60, 30, Outcome.TRIUMPH),  # under by exactly 30
        (60, 31, Outcome.SUCCESS),  # under by 29
        (60, 60, Outcome.SUCCESS),  # at the chance
        (60, 61, Outcome.SUCCESS_AT_COST),  # over by 1
        (60, 70, Outcome.SUCCESS_AT_COST),  # over by exactly 10
        (60, 71, Outcome.FAILURE),  # over by 11
        (20, 21, Outcome.SUCCESS_AT_COST),
        (20, 31, Outcome.FAILURE),
    ],
)
def test_eng04_outcome_band_edges(chance: int, roll: int, expected: Outcome) -> None:
    assert outcome_for(chance, roll) == expected


@pytest.mark.parametrize(
    ("chance", "roll", "expected"),
    [
        (60, 5, Outcome.TRIUMPH),  # already Triumph stays Triumph
        (30, 5, Outcome.TRIUMPH),  # Success upgrades (under by 25)
        (30, 1, Outcome.TRIUMPH),  # under by 29: Success upgrades
        (3, 4, Outcome.TRIUMPH),  # over the chance, still succeeds, then upgrades (D-028)
        (-40, 1, Outcome.TRIUMPH),  # far over the chance (D-028)
        (-40, 6, Outcome.FAILURE),  # 06 gets no help
    ],
)
def test_eng04_roll_of_01_to_05_succeeds_and_upgrades(chance: int, roll: int, expected: Outcome) -> None:
    assert outcome_for(chance, roll) == expected


@pytest.mark.parametrize(("roll", "complication"), [(95, False), (96, True), (99, True), (100, True)])
def test_eng04_roll_of_96_to_00_adds_a_complication(roll: int, complication: bool) -> None:
    assert resolve_check(FixedRolls(roll), request()).complication is complication


def test_eng04_complication_applies_to_any_outcome() -> None:
    # Chance 110 (Routine 60, +2 gap 40, rank 2 is 10): roll 100 is under by 10.
    high = request(actor_tier=3, challenge_tier=1, stat=65, skill_rank=2)
    result = resolve_check(FixedRolls(100), high)
    assert result.chance == 110
    assert result.outcome is Outcome.SUCCESS
    assert result.complication is True
    assert resolve_check(FixedRolls(100), request()).outcome is Outcome.FAILURE


def test_eng04_check_rolls_one_d100_on_the_checks_stream() -> None:
    rng = FixedRolls(50)
    result = resolve_check(rng, request())
    assert rng.calls == [("checks", 100)]
    assert (result.chance, result.roll, result.outcome) == (60, 50, Outcome.SUCCESS)


# Tier gaps -4 to +4 on a direct-force action with no Overcome Condition: actor Tier 4 (par 80).
@pytest.mark.parametrize(
    ("gap", "chance", "automatic", "outcome"),
    [
        (-4, None, True, Outcome.FAILURE),
        (-3, None, True, Outcome.FAILURE),
        (-2, 20, False, Outcome.FAILURE),
        (-1, 40, False, Outcome.FAILURE),
        (0, 60, False, Outcome.SUCCESS_AT_COST),
        (1, 80, False, Outcome.SUCCESS),
        (2, 100, False, Outcome.TRIUMPH),
        (3, None, True, Outcome.SUCCESS),
        (4, None, True, Outcome.SUCCESS),
    ],
)
def test_eng05_tier_gaps_on_force(gap: int, chance: int | None, automatic: bool, outcome: Outcome) -> None:
    rng = FixedRolls(70)
    result = resolve_check(
        rng, request(stat=80, actor_tier=4, challenge_tier=4 - gap, approach=Approach.FORCE)
    )
    assert result.chance == chance
    assert result.automatic is automatic
    assert result.outcome is outcome
    assert result.tier_gap == gap
    assert result.roll == (None if automatic else 70)
    assert len(rng.calls) == (0 if automatic else 1)
    assert not (automatic and result.complication)


def test_eng05_auto_fail_only_on_direct_force() -> None:
    result = resolve_check(FixedRolls(3), request(challenge_tier=5, approach=Approach.OTHER))
    assert result.automatic is False
    assert result.chance == 60 - 80
    assert result.outcome is Outcome.TRIUMPH


def test_eng05_auto_success_applies_to_any_approach() -> None:
    for approach in Approach:
        rng = FixedRolls()
        result = resolve_check(rng, request(actor_tier=4, stat=80, challenge_tier=1, approach=approach))
        assert (result.automatic, result.outcome) == (True, Outcome.SUCCESS)


@pytest.mark.parametrize(
    "claim",
    [
        OvercomeClaim(OvercomeKind.OATH),
        OvercomeClaim(OvercomeKind.TERRAIN),
        OvercomeClaim(OvercomeKind.ARTIFACT, tier=5),
        OvercomeClaim(OvercomeKind.ARTIFACT, tier=6),
        OvercomeClaim(OvercomeKind.ALLY, tier=5),
        OvercomeClaim(OvercomeKind.DIVINE_FAVOR, standing=60),
    ],
)
def test_eng05_satisfied_overcome_rolls_at_gap_minus_2(claim: OvercomeClaim) -> None:
    result = resolve_check(FixedRolls(10), request(challenge_tier=5, approach=Approach.FORCE, overcome=claim))
    assert result.overcome_applied is True
    assert result.automatic is False
    assert result.tier_gap == -2
    assert result.chance == 60 - 40
    assert result.outcome is Outcome.SUCCESS


@pytest.mark.parametrize(
    "claim",
    [
        OvercomeClaim(OvercomeKind.ARTIFACT, tier=4),
        OvercomeClaim(OvercomeKind.ARTIFACT),
        OvercomeClaim(OvercomeKind.ALLY, tier=4),
        OvercomeClaim(OvercomeKind.ALLY),
        OvercomeClaim(OvercomeKind.DIVINE_FAVOR, standing=59),
        OvercomeClaim(OvercomeKind.DIVINE_FAVOR),
    ],
)
def test_eng05_unsatisfied_overcome_still_fails_without_a_roll(claim: OvercomeClaim) -> None:
    rng = FixedRolls()
    result = resolve_check(rng, request(challenge_tier=5, approach=Approach.FORCE, overcome=claim))
    assert (result.automatic, result.outcome, result.overcome_applied) == (True, Outcome.FAILURE, False)
    assert result.tier_gap == -4
    assert rng.calls == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"challenge_tier": 3, "approach": Approach.FORCE},  # gap -2: no automatic failure to lift
        {"challenge_tier": 5, "approach": Approach.OTHER},  # not direct force
    ],
)
def test_eng05_overcome_is_ignored_when_there_is_no_auto_fail(overrides: dict[str, object]) -> None:
    claim = OvercomeClaim(OvercomeKind.TERRAIN)
    result = resolve_check(FixedRolls(50), request(overcome=claim, **overrides))
    assert result.overcome_applied is False
    assert result.tier_gap == 1 - overrides["challenge_tier"]  # type: ignore[operator]


@pytest.mark.parametrize(
    "overrides",
    [
        {"actor_tier": -1},
        {"actor_tier": 9},
        {"challenge_tier": -1},
        {"challenge_tier": 9},
        {"skill_rank": -1},
        {"skill_rank": 6},
        {"stat": -1},
    ],
)
def test_d022_rejected_request_consumes_no_randomness(overrides: dict[str, object]) -> None:
    rng = FixedRolls()
    with pytest.raises(ValueError):
        resolve_check(rng, request(**overrides))
    assert rng.calls == []


@given(
    difficulty=st.sampled_from(Difficulty),
    stat=st.integers(0, 200),
    skill_rank=st.integers(0, 5),
    actor_tier=st.integers(0, 8),
    challenge_tier=st.integers(0, 8),
    approach=st.sampled_from(Approach),
    roll=st.integers(1, 100),
)
def test_eng04_every_check_obeys_the_natural_roll_rules(
    difficulty: Difficulty,
    stat: int,
    skill_rank: int,
    actor_tier: int,
    challenge_tier: int,
    approach: Approach,
    roll: int,
) -> None:
    result = resolve_check(
        FixedRolls(roll),
        CheckRequest(difficulty, stat, skill_rank, actor_tier, challenge_tier, approach),
    )
    if result.automatic:
        assert result.roll is None
        assert result.chance is None
        assert result.complication is False
        return
    assert result.roll == roll
    assert result.complication is (roll >= 96)
    if roll <= 5:
        assert result.outcome is Outcome.TRIUMPH


def test_eng03_same_seed_and_inputs_give_the_same_results() -> None:
    def run() -> str:
        rng = RngStreams.from_seed(20261030)
        results = [
            resolve_check(
                rng,
                CheckRequest(
                    difficulty=list(Difficulty)[i % 4],
                    stat=20 + i * 3,
                    skill_rank=i % 6,
                    actor_tier=i % 5,
                    challenge_tier=(i * 2) % 7,
                    approach=list(Approach)[i % 2],
                ),
            )
            for i in range(40)
        ]
        log = json.dumps([dataclasses.asdict(r) for r in results], sort_keys=True)
        return hashlib.sha256(log.encode()).hexdigest()

    # The pinned hash also proves Linux CI and the owner's Windows PC agree (D-021).
    assert run() == run() == "5c015f5cc79244ae1aaf908d3a6ce43abae57461f5bdb1044770f46e0d588e11"
