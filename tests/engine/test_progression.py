"""ENG-01, ENG-07: skills, caps, shards, titles, Injuries, Ascension and evolution (M1b, D-037).

The content here is a test fixture, not canon: the real lists are M3.5's canon batches.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pantheon.engine.checks import Outcome
from pantheon.engine.commands import CharacterChoices, choose_class, choose_profession, create_character
from pantheon.engine.progression import (
    absorb_shard,
    affinity_cap,
    choose_evolution,
    evolution_options,
    fuse_fragments,
    grant_title,
    pick_skill,
    skill_rank_cap,
)
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import GameState, Shard, replay, xp_to_next
from pantheon.engine.timeline import Rejected, Rules, Simulation
from pantheon.engine.tools import apply_tool, attempt_trial, resolve_offer
from pantheon.world.loader import load_world
from pantheon.world.schemas import Evolution, GameData, Skill, Title

WORLD = load_world(Path(__file__).resolve().parents[2] / "world")
assert WORLD.data is not None
CONTENT: GameData = WORLD.data.model_copy(
    update={
        "skills": (
            Skill(id="tide_step", name="Tide Step", affinity="tide", rarity="common", classes=("wayfinder",)),
            Skill(id="undertow", name="Undertow", affinity="tide", rarity="uncommon", classes=("wayfinder",)),
            Skill(id="plain_talk", name="Plain Talk", rarity="common", classes=("wayfinder",)),
            Skill(id="pathmark", name="Pathmark", rarity="common", classes=("wayfinder",)),
            Skill(id="ember", name="Ember", affinity="flame", rarity="common", classes=("wayfinder",)),
            Skill(id="tide_lord", name="Tide Lord", affinity="tide", rarity="mythic"),
        ),
        "titles": (
            Title(id="stair_survivor", name="Stair Survivor", stat="vigor", stat_bonus=2),
            Title(
                id="unwitnessed", name="Quiet Deed", needs_witness=False, check_kind="stealth", check_bonus=5
            ),
        ),
        "evolutions": (
            Evolution(
                id="tide_walker",
                name="Tide Walker",
                from_class="wayfinder",
                primary="agility",
                secondary="presence",
            ),
            Evolution(
                id="ember_scout",
                name="Ember Scout",
                from_class="wayfinder",
                primary="agility",
                secondary="intellect",
                needs_affinity={"flame": 2},
            ),
            Evolution(
                id="sworn_scout",
                name="Sworn Scout",
                from_class="wayfinder",
                primary="resolve",
                secondary="agility",
                needs_oath="fair_wager",
            ),
            Evolution(
                id="titled_scout",
                name="Titled Scout",
                from_class="wayfinder",
                primary="resolve",
                secondary="agility",
                needs_title="stair_survivor",
                needs_stat={"agility": 200},
            ),
        ),
    }
)
RULES = Rules(CONTENT, {k: f.set_by for k, f in WORLD.flags.items()})
STATS = {"vigor": 30, "agility": 27, "intellect": 24, "resolve": 20, "presence": 18}


def fresh(seed: int = 1) -> Simulation:
    sim = Simulation(GameState(), RngStreams.from_seed(seed), RULES, 0)
    sim.emit("opening_gods_drawn", {"gods": ["drovash", "veshra"]})
    create_character(
        sim,
        CharacterChoices(
            name="Wren",
            people="saltborn",
            origin="toll_ferry_orphan",
            age=20,
            flaw="Hoards small objects",
            debt="A name owed",
            stats=STATS,
        ),
    )
    return sim


def sworn(seed: int = 1) -> Simulation:
    sim = fresh(seed)
    resolve_offer(sim, "drovash")
    choose_class(sim, "wayfinder")
    choose_profession(sim, "alchemist")
    return sim


def give(sim: Simulation, kind: str, target: str, rarity: str = "common", *, fragment: bool = False) -> None:
    sim.emit("shard_gained", {"kind": kind, "target": target, "rarity": rarity, "fragment": fragment})


def set_level(sim: Simulation, level: int) -> None:
    sim.emit("level_up", {"level": level, "xp_spent": 0, "gains": {}, "free_points": 0})


def test_eng07_level_one_offers_three_class_skills_the_character_can_use() -> None:
    sim = sworn()
    assert len(sim.state.skill_offers) == 1
    offer = sim.state.skill_offers[0]
    assert len(offer) == 3 and "ember" not in offer  # Flame rank 0 cannot hold a Flame skill.


def test_eng07_picking_learns_the_skill_at_rank_one_and_clears_the_offer() -> None:
    sim = sworn()
    choice = sim.state.skill_offers[0][0]
    pick_skill(sim, choice)
    assert sim.state.skills[choice] == 1
    assert sim.state.skill_rarity[choice] == {s.id: s.rarity for s in CONTENT.skills}[choice]
    assert sim.state.skill_offers == []
    with pytest.raises(Rejected):
        pick_skill(sim, choice)


def test_eng07_only_an_offered_skill_can_be_picked() -> None:
    sim = sworn()
    with pytest.raises(Rejected):
        pick_skill(sim, "ember")


@pytest.mark.parametrize(
    ("level", "offered"), [(2, False), (3, True), (5, True), (7, True), (9, True), (10, False)]
)
def test_eng07_skill_offers_come_at_odd_levels_of_a_tier(level: int, offered: bool) -> None:
    sim = sworn()
    pick_skill(sim, sim.state.skill_offers[0][0])
    sim.emit("level_up", {"level": level - 1, "xp_spent": 0, "gains": {}, "free_points": 0})
    sim.emit("xp_gained", {"amount": xp_to_next(level - 1), "kind": "x", "reason": "x"})
    apply_tool(sim, "grant_xp", {"kind": "minor", "reason": "a push"})
    assert sim.state.level == level
    assert bool(sim.state.skill_offers) is offered


def test_d037_no_content_means_no_offer_and_no_randomness() -> None:
    sim = Simulation(GameState(), RngStreams.from_seed(1), Rules(WORLD.data, {}), 0)  # type: ignore[arg-type]
    before = sim.rng.state()
    sim.emit("level_up", {"level": 1, "xp_spent": 0, "gains": {}, "free_points": 0})
    sim.emit("class_chosen", {"class_id": "wayfinder"})
    from pantheon.engine.progression import offer_skills

    offer_skills(sim)
    assert sim.state.skill_offers == [] and sim.rng.state() == before


@pytest.mark.parametrize(("level", "cap"), [(1, 2), (10, 2), (11, 3), (21, 4), (31, 5), (70, 5)])
def test_eng07_skill_rank_cap_follows_tier(level: int, cap: int) -> None:
    state = GameState(level=level, affinities={"tide": 5})
    assert skill_rank_cap(state, "tide") == cap
    assert skill_rank_cap(state, None) == cap


def test_eng07_a_skill_rank_never_exceeds_its_affinity_rank() -> None:
    state = GameState(level=31, affinities={"tide": 1})
    assert skill_rank_cap(state, "tide") == 1
    assert skill_rank_cap(state, "frost") == 0


@pytest.mark.parametrize(("ranks", "cap"), [({}, 1), ({"tide": 1}, 1), ({"tide": 3}, 3)])
def test_d013_the_unwrittens_skill_cap_is_their_best_affinity(ranks: dict[str, int], cap: int) -> None:
    assert skill_rank_cap(GameState(level=0, affinities=ranks), None) == cap


@pytest.mark.parametrize(("level", "cap"), [(0, 3), (1, 2), (11, 3), (70, 8)])
def test_eng07_affinity_cap(level: int, cap: int) -> None:
    assert affinity_cap(GameState(level=level)) == cap


def test_eng07_an_affinity_shard_raises_the_rank_up_to_its_cap() -> None:
    sim = sworn()
    give(sim, "affinity", "flame")
    give(sim, "affinity", "flame")
    give(sim, "affinity", "flame")
    absorb_shard(sim, 0)
    absorb_shard(sim, 0)
    assert sim.state.affinities["flame"] == 2 and len(sim.state.shards) == 1
    with pytest.raises(Rejected, match="cap"):
        absorb_shard(sim, 0)
    assert len(sim.state.shards) == 1  # A refused shard is not used up.


def test_eng07_a_skill_shard_teaches_a_new_skill_if_the_affinity_is_there() -> None:
    sim = sworn()
    give(sim, "skill", "ember")
    with pytest.raises(Rejected, match="affinity"):
        absorb_shard(sim, 0)
    give(sim, "affinity", "flame")
    absorb_shard(sim, 1)
    absorb_shard(sim, 0)
    assert sim.state.skills["ember"] == 1


def test_eng07_a_matching_skill_shard_upgrades_up_to_the_cap() -> None:
    sim = sworn()
    sim.emit("affinity_raised", {"affinity": "tide", "rank": 2})
    sim.emit("skill_gained", {"skill": "tide_step", "rank": 1, "rarity": "common"})
    give(sim, "skill", "tide_step")
    give(sim, "skill", "tide_step")
    absorb_shard(sim, 0)
    assert sim.state.skills["tide_step"] == 2
    with pytest.raises(Rejected, match="cap"):
        absorb_shard(sim, 0)


def test_eng07_a_skill_shard_of_the_wrong_rarity_does_not_upgrade() -> None:
    sim = sworn()
    sim.emit("skill_gained", {"skill": "tide_step", "rank": 1, "rarity": "common"})
    give(sim, "skill", "tide_step", "rare")
    with pytest.raises(Rejected, match="rarity"):
        absorb_shard(sim, 0)


def test_d037_rank_five_and_a_matching_shard_evolve_the_skill_to_rank_one_of_the_next_rarity() -> None:
    sim = sworn()
    set_level(sim, 31)
    sim.emit("affinity_raised", {"affinity": "tide", "rank": 5})
    sim.emit("skill_gained", {"skill": "tide_step", "rank": 5, "rarity": "common"})
    give(sim, "skill", "tide_step")
    absorb_shard(sim, 0)
    assert sim.state.skills["tide_step"] == 1 and sim.state.skill_rarity["tide_step"] == "uncommon"


@pytest.mark.parametrize(("level", "ok"), [(31, False), (51, True)])
def test_eng07_mythic_needs_tier_six(level: int, ok: bool) -> None:
    sim = sworn()
    set_level(sim, level)
    sim.emit("affinity_raised", {"affinity": "tide", "rank": 5})
    sim.emit("skill_gained", {"skill": "tide_lord", "rank": 5, "rarity": "legendary"})
    give(sim, "skill", "tide_lord", "legendary")
    if ok:
        absorb_shard(sim, 0)
        assert sim.state.skill_rarity["tide_lord"] == "mythic"
    else:
        with pytest.raises(Rejected, match="Tier"):
            absorb_shard(sim, 0)


def test_eng07_fragments_cannot_be_absorbed_and_three_fuse_into_a_shard() -> None:
    sim = fresh()
    for _ in range(3):
        give(sim, "affinity", "flame", fragment=True)
    with pytest.raises(Rejected, match="fragment"):
        absorb_shard(sim, 0)
    fuse_fragments(sim, "affinity", "flame")
    assert sim.state.shards == [Shard(kind="affinity", target="flame", rarity="common", fragment=False)]


def test_eng07_too_few_fragments_do_not_fuse() -> None:
    sim = fresh()
    give(sim, "affinity", "flame", fragment=True)
    give(sim, "affinity", "flame", fragment=True)
    with pytest.raises(Rejected, match="3"):
        fuse_fragments(sim, "affinity", "flame")


def test_d037_a_hearthwright_fuses_from_two() -> None:
    sim = fresh()
    resolve_offer(sim, "drovash")
    choose_class(sim, "hearthwright")
    give(sim, "affinity", "flame", fragment=True)
    give(sim, "affinity", "flame", fragment=True)
    fuse_fragments(sim, "affinity", "flame")
    assert [s.fragment for s in sim.state.shards] == [False]


def test_d013_the_unwritten_can_absorb_shards() -> None:
    sim = fresh()
    give(sim, "affinity", "flame")
    absorb_shard(sim, 0)
    assert sim.state.affinities["flame"] == 1


def test_absorbing_a_missing_shard_is_rejected() -> None:
    with pytest.raises(Rejected):
        absorb_shard(sworn(), 4)


def test_eng07_a_title_needs_a_witness_and_gives_its_bonus_once() -> None:
    sim = sworn()
    vigor = sim.state.stats["vigor"]
    with pytest.raises(Rejected, match="witness"):
        grant_title(sim, "stair_survivor", witness="none")
    grant_title(sim, "stair_survivor", witness="npc:hale")
    assert sim.state.stats["vigor"] == vigor + 2 and sim.state.titles == ["stair_survivor"]
    with pytest.raises(Rejected, match="already"):
        grant_title(sim, "stair_survivor", witness="npc:hale")
    with pytest.raises(Rejected, match="unknown"):
        grant_title(sim, "no_such_title", witness="npc:hale")
    grant_title(sim, "unwitnessed", witness="none")
    assert sim.state.titles == ["stair_survivor", "unwitnessed"]


def trial_ready(seed: int = 1) -> Simulation:
    sim = sworn(seed)
    sim.emit("skill_offers_cleared", {})
    set_level(sim, 10)
    sim.emit("xp_gained", {"amount": xp_to_next(10), "kind": "x", "reason": "x"})
    return sim


def seed_for(outcomes: set[Outcome]) -> int:
    """A seed whose first trial roll lands on one of these outcomes, read from the real engine."""
    for seed in range(1, 400):
        probe = trial_ready(seed)
        attempt_trial(probe)
        rolled = next(p for t, p in probe.events if t == "check_resolved")
        if Outcome(rolled["outcome"]) in outcomes:
            return seed
    raise AssertionError("no seed found")


def test_eng07_the_trial_waits_for_the_gate() -> None:
    sim = sworn()
    with pytest.raises(Rejected):
        attempt_trial(sim)
    set_level(sim, 10)
    with pytest.raises(Rejected):
        attempt_trial(sim)  # Level 10, but XP has not filled.


def test_d037_success_ascends_and_offers_evolution() -> None:
    sim = trial_ready(seed_for({Outcome.SUCCESS, Outcome.TRIUMPH}))
    xp = sim.state.xp
    assert attempt_trial(sim)["result"] == "ascend"
    assert sim.state.level == 11 and sim.state.needs_evolution and sim.state.xp == xp - xp_to_next(10)
    rolled = next(p for t, p in sim.events if t == "check_resolved")
    assert rolled["challenge_tier"] == 2  # Set at the next tier.


def test_d037_a_narrow_miss_is_a_setback_that_loses_the_levels_xp() -> None:
    sim = trial_ready(seed_for({Outcome.SUCCESS_AT_COST}))
    assert attempt_trial(sim)["result"] == "setback"
    assert sim.state.level == 10 and sim.state.xp == 0 and sim.state.trial_recovery


def test_d037_failure_is_a_breaking_with_an_injury() -> None:
    sim = trial_ready(seed_for({Outcome.FAILURE}))
    before = dict(sim.state.stats)
    assert attempt_trial(sim)["result"] == "breaking"
    assert sim.state.level == 10 and sim.state.trial_recovery
    assert len(sim.state.injuries) == 1
    injury = sim.state.injuries[0]
    assert sim.state.stats[injury.stat] == max(0, before[injury.stat] - 10)


def test_d037_a_trial_cannot_be_retried_until_after_a_rest() -> None:
    sim = trial_ready(seed_for({Outcome.FAILURE}))
    attempt_trial(sim)
    with pytest.raises(Rejected, match="recover"):
        attempt_trial(sim)
    result = apply_tool(sim, "apply_effect", {"kind": "heal", "source": "rest", "reason": "a long sleep"})
    assert result.accepted and not sim.state.trial_recovery
    attempt_trial(sim)
    assert sum(1 for t, _ in sim.events if t == "trial_resolved") == 2


def test_eng07_only_met_requirements_unlock_an_evolution() -> None:
    sim = sworn()
    ids = {e.id for e in evolution_options(sim.state, CONTENT)}
    assert ids == {"tide_walker", "sworn_scout"}  # Fair Wager is sworn; no Flame 2; no title.
    sim.emit("affinity_raised", {"affinity": "flame", "rank": 2})
    assert "ember_scout" in {e.id for e in evolution_options(sim.state, CONTENT)}
    assert "titled_scout" not in {e.id for e in evolution_options(sim.state, CONTENT)}


def test_eng07_evolving_changes_the_class_adds_five_and_later_gains_follow_it() -> None:
    sim = trial_ready(seed_for({Outcome.SUCCESS, Outcome.TRIUMPH}))
    attempt_trial(sim)
    with pytest.raises(Rejected):
        choose_evolution(sim, "ember_scout")
    agility = sim.state.stats["agility"]
    presence = sim.state.stats["presence"]
    choose_evolution(sim, "tide_walker")
    assert sim.state.class_id == "tide_walker" and not sim.state.needs_evolution
    assert sim.state.stats["agility"] == agility + 5
    sim.emit("xp_gained", {"amount": xp_to_next(11), "kind": "x", "reason": "x"})
    apply_tool(sim, "grant_xp", {"kind": "minor", "reason": "a push"})
    assert sim.state.level == 12
    assert sim.state.stats["presence"] == presence + 1  # Tide Walker's secondary stat.


def test_d037_with_no_evolution_data_the_class_carries_on() -> None:
    sim = sworn()
    sim.emit("level_up", {"level": 10, "xp_spent": 0, "gains": {}, "free_points": 0})
    bare = Simulation(sim.state, RngStreams.from_seed(1), Rules(WORLD.data, {}), 1)  # type: ignore[arg-type]
    bare.emit("xp_gained", {"amount": xp_to_next(10), "kind": "x", "reason": "x"})
    for seed in range(1, 200):
        trial = Simulation(bare.state, RngStreams.from_seed(seed), bare.rules, 1)
        if attempt_trial(trial)["result"] == "ascend":
            assert not trial.state.needs_evolution
            return
    raise AssertionError("no ascending seed found")


Step = tuple[str, Any]


@settings(max_examples=40, deadline=None)
@given(
    st.lists(
        st.one_of(
            st.tuples(st.just("give"), st.sampled_from(["flame", "tide"])),
            st.tuples(st.just("frag"), st.sampled_from(["flame", "tide"])),
            st.tuples(st.just("absorb"), st.integers(0, 3)),
            st.tuples(st.just("fuse"), st.sampled_from(["flame", "tide"])),
            st.tuples(st.just("title"), st.sampled_from(["stair_survivor", "unwitnessed"])),
        ),
        max_size=25,
    )
)
def test_eng06_replay_equals_live_state_and_caps_hold(steps: list[Step]) -> None:
    sim = sworn()
    for action, value in steps:
        try:
            if action == "give":
                give(sim, "affinity", value)
            elif action == "frag":
                give(sim, "affinity", value, fragment=True)
            elif action == "absorb":
                absorb_shard(sim, value)
            elif action == "fuse":
                fuse_fragments(sim, "affinity", value)
            else:
                grant_title(sim, value, witness="npc:hale")
        except Rejected:
            pass
    assert all(rank <= affinity_cap(sim.state) for rank in sim.state.affinities.values())
    assert replay(sim.events).model_dump() == sim.state.model_dump()
    json.dumps([payload for _, payload in sim.events])
