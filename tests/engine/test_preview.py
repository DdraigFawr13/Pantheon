"""One home for D-050 and D-051: the preview rule, the stat lock and the closing-thought odds."""

from pantheon.engine.preview import chance, lock, needs_preview, preview_text, stamp_odds
from pantheon.engine.state import Action
from pantheon.engine.tools import check_preview
from tests.conftest import WORLD
from tests.narrator.test_loop import sworn_state

assert WORLD.data is not None
DATA = WORLD.data
HARD = {"stat": "agility", "difficulty": "hard", "challenge_tier": 0, "stakes": "a fall"}


def test_nar08_only_hard_or_harder_checks_preview() -> None:
    assert needs_preview(HARD) and needs_preview({**HARD, "difficulty": "heroic"})
    assert not needs_preview({**HARD, "difficulty": "routine"})


def test_nar08_a_stats_first_preview_fixes_its_difficulty_and_tier_for_the_turn() -> None:
    seen: dict[str, dict] = {}
    assert lock(seen, HARD) == HARD
    reworded = {**HARD, "difficulty": "routine", "challenge_tier": 2, "stakes": "a slip"}
    assert lock(seen, reworded) == {**reworded, "difficulty": "hard", "challenge_tier": 0}
    other = {"stat": "presence", "difficulty": "routine", "challenge_tier": 0}
    assert lock(seen, other) == other and set(seen) == {"agility", "presence"}


def test_d036_chance_and_preview_text_come_from_the_roll_calculation() -> None:
    state, _ = sworn_state()
    shown = check_preview(state, DATA, HARD).shown
    assert chance(state, DATA, HARD) == f"{shown}%"
    assert preview_text(state, DATA, HARD) == f"Agility check, hard: {shown}%"


def test_d050_stamp_odds_prints_each_marked_approach_and_removes_strays() -> None:
    state, _ = sworn_state()
    state.suggested = [Action(label="Ask"), Action(label="Climb", check=HARD)]
    text, shown, missing = stamp_odds("Ask <<ODDS 1>>, climb <<ODDS 2>>, or fly <<ODDS 5>>.", state, DATA)
    assert text == f"Ask (no roll), climb (Agility {chance(state, DATA, HARD)}), or fly."
    assert shown == [1, 2] and missing == [5]
