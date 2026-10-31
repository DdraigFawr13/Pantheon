"""d100 checks (ENG-04, ENG-05). Rules: `world/power_tiers.md` Checks; assumptions: D-028."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pantheon.engine.rng import RngStreams

MIN_TIER, MAX_TIER = 0, 8
MIN_SKILL_RANK, MAX_SKILL_RANK = 0, 5
AUTO_SUCCESS_GAP = 3
AUTO_FAIL_GAP = -3
OVERCOME_GAP = -2
DIVINE_FAVOR_STANDING = 60
ALWAYS_SUCCEEDS = 5


class Difficulty(StrEnum):
    ROUTINE = "routine"
    HARD = "hard"
    SEVERE = "severe"
    HEROIC = "heroic"


DIFFICULTY_VALUES = {
    Difficulty.ROUTINE: 60,
    Difficulty.HARD: 40,
    Difficulty.SEVERE: 20,
    Difficulty.HEROIC: 0,
}


class Approach(StrEnum):
    FORCE = "force"
    OTHER = "other"


class Outcome(StrEnum):
    FAILURE = "failure"
    SUCCESS_AT_COST = "success_at_cost"
    SUCCESS = "success"
    TRIUMPH = "triumph"


class OvercomeKind(StrEnum):
    OATH = "oath"
    ARTIFACT = "artifact"
    TERRAIN = "terrain"
    ALLY = "ally"
    DIVINE_FAVOR = "divine_favor"


@dataclass(frozen=True, slots=True)
class OvercomeClaim:
    """`tier` and `standing` come from engine state, never from the narrator."""

    kind: OvercomeKind
    tier: int | None = None
    standing: int | None = None

    def satisfied(self, challenge_tier: int) -> bool:
        match self.kind:
            case OvercomeKind.ARTIFACT | OvercomeKind.ALLY:
                return self.tier is not None and self.tier >= challenge_tier
            case OvercomeKind.DIVINE_FAVOR:
                return self.standing is not None and self.standing >= DIVINE_FAVOR_STANDING
            case OvercomeKind.OATH | OvercomeKind.TERRAIN:
                return True  # Whether these apply is the narrator's judgement (architecture section 6).


@dataclass(frozen=True, slots=True)
class CheckRequest:
    difficulty: Difficulty
    stat: int
    skill_rank: int
    actor_tier: int
    challenge_tier: int
    approach: Approach
    overcome: OvercomeClaim | None = None


@dataclass(frozen=True, slots=True)
class CheckResult:
    """`chance` and `roll` are None when the tier gap settled the check without a roll."""

    outcome: Outcome
    automatic: bool
    tier_gap: int
    overcome_applied: bool
    chance: int | None
    roll: int | None
    complication: bool


def par(tier: int) -> int:
    return 20 + 15 * tier


def stat_edge(stat: int, actor_tier: int) -> int:
    return (stat - par(actor_tier)) // 5


def base_chance(difficulty: Difficulty, stat: int, skill_rank: int, actor_tier: int, tier_gap: int) -> int:
    return DIFFICULTY_VALUES[difficulty] + stat_edge(stat, actor_tier) + 5 * skill_rank + 20 * tier_gap


def outcome_for(chance: int, roll: int) -> Outcome:
    if roll <= ALWAYS_SUCCEEDS:
        return Outcome.TRIUMPH  # Always succeeds, then upgrades one step (D-028).
    if chance - roll >= 30:
        return Outcome.TRIUMPH
    if roll <= chance:
        return Outcome.SUCCESS
    if roll - chance <= 10:
        return Outcome.SUCCESS_AT_COST
    return Outcome.FAILURE


def _validate(request: CheckRequest) -> None:
    for name, tier in (("actor_tier", request.actor_tier), ("challenge_tier", request.challenge_tier)):
        if not MIN_TIER <= tier <= MAX_TIER:
            raise ValueError(f"{name} must be {MIN_TIER} to {MAX_TIER}, got {tier}")
    if not MIN_SKILL_RANK <= request.skill_rank <= MAX_SKILL_RANK:
        raise ValueError(f"skill_rank must be {MIN_SKILL_RANK} to {MAX_SKILL_RANK}, got {request.skill_rank}")
    if request.stat < 0:
        raise ValueError(f"stat must not be negative, got {request.stat}")


@dataclass(frozen=True, slots=True)
class CheckOdds:
    """What a check will do before it rolls. `outcome` is set when the tier gap settles it (D-036)."""

    outcome: Outcome | None
    tier_gap: int
    overcome_applied: bool
    chance: int | None

    @property
    def shown(self) -> int | None:
        """The chance as a player sees it: low rolls always succeed, and the d100 stops at 100."""
        return None if self.chance is None else max(ALWAYS_SUCCEEDS, min(100, self.chance))


def check_odds(request: CheckRequest) -> CheckOdds:
    """The one calculation behind both the odds on screen and the roll (GAME-02)."""
    _validate(request)
    tier_gap = request.actor_tier - request.challenge_tier
    overcome_applied = False

    if tier_gap >= AUTO_SUCCESS_GAP:
        return CheckOdds(Outcome.SUCCESS, tier_gap, False, None)
    if tier_gap <= AUTO_FAIL_GAP and request.approach is Approach.FORCE:
        if request.overcome is None or not request.overcome.satisfied(request.challenge_tier):
            return CheckOdds(Outcome.FAILURE, tier_gap, False, None)
        tier_gap = OVERCOME_GAP
        overcome_applied = True

    chance = base_chance(request.difficulty, request.stat, request.skill_rank, request.actor_tier, tier_gap)
    return CheckOdds(None, tier_gap, overcome_applied, chance)


def resolve_check(rng: RngStreams, request: CheckRequest) -> CheckResult:
    """Validate, then roll on the `checks` stream. A rejected request consumes no randomness (D-022)."""
    odds = check_odds(request)
    if odds.outcome is not None or odds.chance is None:
        assert odds.outcome is not None
        return CheckResult(odds.outcome, True, odds.tier_gap, False, None, None, False)
    roll = rng.roll("checks", 100)
    outcome = outcome_for(odds.chance, roll)
    return CheckResult(outcome, False, odds.tier_gap, odds.overcome_applied, odds.chance, roll, roll >= 96)
