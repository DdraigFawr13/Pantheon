"""ENG-01, ENG-02, ENG-06, ENG-09, NAR-03: the thin slice's tools, commands and fold (D-029, D-030)."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pantheon.engine.commands import (
    CharacterChoices,
    allocate_point,
    choose_class,
    choose_profession,
    create_character,
)
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import GameState, replay, xp_to_next
from pantheon.engine.timeline import Rejected, Rules, Simulation
from pantheon.engine.tools import (
    apply_tool,
    check_preview,
    resolve_offer,
    tool_definition,
    tool_definitions,
)
from pantheon.world.loader import load_world

WORLD = load_world(Path(__file__).resolve().parents[2] / "world")
assert WORLD.data is not None
RULES = Rules(WORLD.data, {k: f.set_by for k, f in WORLD.flags.items()})
STATS = {"vigor": 30, "agility": 27, "intellect": 24, "resolve": 20, "presence": 18}
CHOICES = CharacterChoices(
    name="Wren",
    people="saltborn",
    origin="toll_ferry_orphan",
    age=20,
    flaw="Hoards small objects",
    debt="A name owed",
    stats=STATS,
)


def fresh(seed: int = 1, gods: tuple[str, str] = ("drovash", "veshra")) -> Simulation:
    sim = Simulation(GameState(), RngStreams.from_seed(seed), RULES, 0)
    sim.emit("opening_gods_drawn", {"gods": list(gods)})
    create_character(sim, CHOICES)
    return sim


def sworn(seed: int = 1) -> Simulation:
    sim = fresh(seed)
    resolve_offer(sim, "drovash")
    choose_class(sim, "wager_bound")
    choose_profession(sim, "merchant")
    return sim


def next_turn(sim: Simulation) -> Simulation:
    return Simulation(sim.state, sim.rng, sim.rules, sim.turn + 1)


def test_character_creation_applies_people_and_origin_and_offers_both_oaths() -> None:
    state = fresh().state
    assert state.stats["presence"] == 18 + 3
    assert state.stats["agility"] == 27 + 2
    assert state.affinities == {"tide": 1}
    assert state.skills == {"streetwise": 1}
    assert state.standing == {"harbors": 5, "underlanes": 5}
    assert state.coin == 12
    assert state.tier == 0 and state.level == 0
    assert sorted(state.offers) == ["fair_wager", "open_hand"]
    assert state.hooks[0].description == "Debt: A name owed"


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": " "},
        {"age": 15},
        {"stats": {**STATS, "vigor": 31}},
        {"people": "nobody"},
        {"origin": "nobody"},
        {"people": "fenfolk", "innate_affinity": "flame"},
        {"people": "humans", "innate_affinity": "flame"},
    ],
)
def test_bad_character_is_rejected(overrides: dict[str, Any]) -> None:
    sim = Simulation(GameState(), RngStreams.from_seed(1), RULES, 0)
    with pytest.raises(Rejected):
        create_character(sim, CHOICES.model_copy(update=overrides))
    assert sim.events == []


def test_character_cannot_be_created_twice() -> None:
    with pytest.raises(Rejected):
        create_character(fresh(), CHOICES)


def test_swearing_sets_level_one_blessing_and_hooks() -> None:
    sim = fresh()
    assert resolve_offer(sim, "drovash")["sworn"] == "fair_wager"
    state = sim.state
    assert (state.level, state.tier) == (1, 1)
    assert state.affinities["shadow"] == 1
    assert state.oaths == ["fair_wager"]
    assert state.flags["opening.dual_offer_resolved"] is True
    assert state.needs_class and state.needs_profession
    descriptions = [h.description for h in state.hooks]
    assert any("Drovash's answer" in d for d in descriptions)
    assert any("Veshra's response to being refused" in d for d in descriptions)
    assert any("Open Hand to Veshra" in d for d in descriptions)


def test_refusing_both_stays_unwritten_with_a_seeded_rival() -> None:
    a, b = fresh(5), fresh(5)
    resolve_offer(a, "refuse")
    resolve_offer(b, "refuse")
    assert a.state.level == 0
    assert a.state.flags["unwritten_path"] is True
    assert a.events == b.events


@pytest.mark.parametrize("choice", ["kaul", "nonsense"])
def test_offer_rejects_a_god_who_did_not_speak(choice: str) -> None:
    sim = fresh()
    with pytest.raises(Rejected):
        resolve_offer(sim, choice)
    assert not sim.state.offer_resolved


def test_offer_resolves_once() -> None:
    with pytest.raises(Rejected):
        resolve_offer(sworn(), "veshra")


def test_the_narrator_cannot_decide_the_dual_offer() -> None:
    sim = fresh()
    assert not apply_tool(sim, "resolve_dual_offer", {"choice": "refuse"}).accepted
    assert not sim.state.offer_resolved
    assert "resolve_dual_offer" not in {t["name"] for t in tool_definitions()}


def test_eng02_unknown_tool_and_bad_args_are_rejected_with_a_reason() -> None:
    sim = fresh()
    unknown = apply_tool(sim, "summon_dragon", {})
    assert not unknown.accepted and "unknown tool" in unknown.payload()["reason"]
    bad = apply_tool(sim, "request_check", {"stat": "luck", "difficulty": "hard", "challenge_tier": 1})
    assert not bad.accepted and "stat" in bad.reason
    assert sim.events[-1][0] != "check_resolved"


def test_eng09_check_returns_engine_values_and_records_outcome() -> None:
    sim = sworn(3)
    result = apply_tool(
        sim,
        "request_check",
        {"stat": "agility", "skill": "Streetwise", "difficulty": "hard", "challenge_tier": 1},
    )
    assert result.accepted and result.data["check_id"] == "c1"
    event = next(p for t, p in sim.events if t == "check_resolved")
    assert event["skill_rank"] == 1
    assert event["chance"] == 40 + (29 - 35) // 5 + 5
    assert event["roll"] is not None


def test_unknown_skill_counts_as_rank_zero() -> None:
    sim = sworn()
    apply_tool(
        sim,
        "request_check",
        {"stat": "vigor", "skill": "juggling", "difficulty": "hard", "challenge_tier": 1},
    )
    assert next(p for t, p in sim.events if t == "check_resolved")["skill_rank"] == 0


def test_eng05_overcome_uses_state_not_the_narrators_word() -> None:
    unsworn = fresh()
    args = {"stat": "vigor", "difficulty": "routine", "challenge_tier": 5, "approach": "force"}
    assert not apply_tool(unsworn, "request_check", {**args, "overcome": "oath"}).accepted
    sim = sworn()
    favour = apply_tool(sim, "request_check", {**args, "overcome": "divine_favor"})
    assert favour.data["automatic"] is True  # Standing below 60
    terrain = apply_tool(sim, "request_check", {**args, "overcome": "terrain"})
    assert terrain.data["automatic"] is False
    oath = apply_tool(sim, "request_check", {**args, "overcome": "oath"})
    assert oath.data["automatic"] is False


def forced_check(sim: Simulation, outcome: str) -> str:
    check_id = f"c{sim.state.checks_made + 1}"
    sim.emit("check_resolved", {"check_id": check_id, "outcome": outcome})
    from pantheon.engine.checks import Outcome

    sim.checks[check_id] = Outcome(outcome)
    return check_id


@pytest.mark.parametrize(("outcome", "percent"), [("failure", 25), ("success_at_cost", 10)])
def test_eng09_damage_size_comes_from_the_outcome(outcome: str, percent: int) -> None:
    sim = sworn()
    check = forced_check(sim, outcome)
    before = sim.state.max_hp
    result = apply_tool(sim, "apply_effect", {"kind": "damage", "source": check, "reason": "fell"})
    assert result.accepted
    assert before - result.data["hp"] == -(-before * percent // 100)


def test_damage_rejects_success_repeats_and_unknown_sources() -> None:
    sim = sworn()
    ok = forced_check(sim, "success")
    assert not apply_tool(sim, "apply_effect", {"kind": "damage", "source": ok, "reason": "x"}).accepted
    bad = forced_check(sim, "failure")
    assert apply_tool(sim, "apply_effect", {"kind": "damage", "source": bad, "reason": "x"}).accepted
    assert not apply_tool(sim, "apply_effect", {"kind": "damage", "source": bad, "reason": "x"}).accepted
    assert not apply_tool(sim, "apply_effect", {"kind": "damage", "source": "c999", "reason": "x"}).accepted
    assert not apply_tool(sim, "apply_effect", {"kind": "heal", "source": "c1", "reason": "x"}).accepted


def test_hazards_down_the_character_and_healing_gets_them_up() -> None:
    sim = sworn()
    hazard = {"kind": "damage", "source": "hazard:rockfall", "reason": "rocks"}
    while not sim.state.downed:
        assert apply_tool(sim, "apply_effect", hazard).accepted
    assert sim.state.hp == 0
    assert not apply_tool(sim, "apply_effect", hazard).accepted
    healed = apply_tool(
        sim, "apply_effect", {"kind": "heal", "source": "aid:a stranger", "reason": "bandaged"}
    )
    assert healed.data["downed"] is False and 0 < healed.data["hp"] < sim.state.max_hp
    apply_tool(sim, "apply_effect", {"kind": "heal", "source": "rest", "reason": "slept"})
    assert sim.state.hp == sim.state.max_hp


def test_eng07_xp_levels_up_with_class_gains_and_a_free_point() -> None:
    sim = sworn()
    before = dict(sim.state.stats)
    assert apply_tool(sim, "grant_xp", {"kind": "milestone", "reason": "deed"}).data["leveled_up"] is True
    assert apply_tool(sim, "grant_xp", {"kind": "minor", "reason": "deed"}).data["leveled_up"] is False
    assert sim.state.level == 2
    assert sim.state.xp == 175 - xp_to_next(1)
    assert sim.state.stats["agility"] == before["agility"] + 2
    assert sim.state.stats["presence"] == before["presence"] + 1
    allocate_point(sim, "resolve")
    assert sim.state.stats["resolve"] == before["resolve"] + 1
    with pytest.raises(Rejected):
        allocate_point(sim, "resolve")


def test_eng07_level_ten_waits_for_a_trial() -> None:
    sim = sworn()
    sim.emit("level_up", {"level": 10, "xp_spent": 0, "gains": {}, "free_points": 0})
    for _ in range(40):
        sim = next_turn(sim)
        result = apply_tool(sim, "grant_xp", {"kind": "milestone", "reason": "deed"})
    assert sim.state.level == 10
    assert result.data["trial_required"] is True


def test_eng09_xp_has_a_per_turn_cap_and_skips_the_unwritten() -> None:
    sim = sworn()
    assert apply_tool(sim, "grant_xp", {"kind": "milestone", "reason": "a"}).accepted
    assert not apply_tool(sim, "grant_xp", {"kind": "major", "reason": "b"}).accepted
    assert apply_tool(next_turn(sim), "grant_xp", {"kind": "major", "reason": "c"}).accepted
    assert not apply_tool(fresh(), "grant_xp", {"kind": "minor", "reason": "d"}).accepted


def test_standing_needs_a_witness_and_clamps() -> None:
    sim = sworn()
    unseen = apply_tool(
        sim, "adjust_standing", {"entity": "kaul", "kind": "grave", "direction": "+", "reason": "alone"}
    )
    assert unseen.data["rumour"] is True and "kaul" not in sim.state.standing
    args = {"entity": "kaul", "kind": "grave", "direction": "-", "witness": "npc:hale", "reason": "seen"}
    for _ in range(10):
        sim = next_turn(sim)
        assert apply_tool(sim, "adjust_standing", args).accepted
    assert sim.state.standing["kaul"] == -100


def test_set_flag_only_takes_story_keys() -> None:
    sim = sworn()
    assert apply_tool(sim, "set_flag", {"key": "story.met_hale", "value": True}).accepted
    assert sim.state.flags["story.met_hale"] is True
    assert not apply_tool(sim, "set_flag", {"key": "rifts_closed", "value": True}).accepted
    assert not apply_tool(sim, "set_flag", {"key": "anything", "value": True}).accepted


def test_nar05_hooks_register_once() -> None:
    sim = sworn()
    args = {"description": "The clerk remembers", "due_condition": "next visit"}
    assert apply_tool(sim, "register_hook", args).accepted
    assert not apply_tool(sim, "register_hook", args).accepted


GOOD = {"label": "Bargain", "violent": False, "cost": "owes a favour"}


@pytest.mark.parametrize(
    ("actions", "ok"),
    [
        ([GOOD, {"label": "Run"}, {"label": "Hit", "violent": True}], True),
        ([GOOD, {"label": "Run"}], False),
        ([GOOD] * 4, True),
        ([GOOD] * 5, False),
        ([{"label": "Hit", "violent": True, "cost": "a wound"}] * 3, False),
        ([{"label": "Run"}, {"label": "Hide"}, {"label": "Wait"}], False),
        ([{"label": "Spend 5 silver", "cost": "coin"}, {"label": "Run"}, {"label": "Hide"}], False),
    ],
)
def test_nar03_suggest_actions_rules(actions: list[dict[str, Any]], ok: bool) -> None:
    sim = sworn()
    assert apply_tool(sim, "suggest_actions", {"actions": actions}).accepted is ok
    assert sim.suggested is ok


@pytest.mark.parametrize(
    ("tag", "ok"),
    [
        ("Fair Wager", True),  # sworn() swears the Oath this tag names.
        ("FAIR WAGER", True),
        ("Open Hand", False),  # An Oath this character does not hold.
        ("sorcery", False),
        ("", False),
    ],
)
def test_d033_action_tags_must_be_something_the_character_has(tag: str, ok: bool) -> None:
    sim = sworn()
    actions = [{**GOOD, "tag": tag}, {"label": "Run"}, {"label": "Hide"}]
    assert apply_tool(sim, "suggest_actions", {"actions": actions}).accepted is ok
    if ok:
        assert sim.state.suggested[0].tag == tag


ROLL = {"stat": "agility", "difficulty": "routine", "challenge_tier": 0, "stakes": "the climb"}


@pytest.mark.parametrize("tag", ["agility", "AGILITY", "streetwise"])
def test_d036_a_stat_or_skill_tag_must_come_with_a_check(tag: str) -> None:
    rest = [{"label": "Run"}, {"label": "Hide"}]
    assert not apply_tool(sworn(), "suggest_actions", {"actions": [{**GOOD, "tag": tag}, *rest]}).accepted
    sim = sworn()
    actions = [{**GOOD, "tag": tag, "check": ROLL}, *rest]
    assert apply_tool(sim, "suggest_actions", {"actions": actions}).accepted
    assert sim.state.suggested[0].check is not None


def test_d036_a_check_with_no_tag_shows_its_skill_or_stat() -> None:
    sim = sworn()
    actions = [
        {**GOOD, "check": ROLL},
        {"label": "Ask around", "check": {**ROLL, "skill": "streetwise"}},
        {"label": "Hide"},
    ]
    assert apply_tool(sim, "suggest_actions", {"actions": actions}).accepted
    assert [a.tag for a in sim.state.suggested] == ["agility", "streetwise", None]


def test_d036_nothing_rolls_before_the_dual_offer_so_no_action_claims_to() -> None:
    sim = fresh()
    actions = [{**GOOD, "tag": "agility", "check": ROLL}, {"label": "Ask", "tag": "presence"}]
    assert apply_tool(sim, "suggest_actions", {"actions": actions}).accepted
    assert all(a.check is None and a.tag is None for a in sim.state.suggested)


def test_d036_the_preview_equals_the_chance_the_roll_uses() -> None:
    sim = sworn()
    assert apply_tool(sim, "suggest_actions", {"actions": [{**GOOD, "check": ROLL}, *[{"label": "Run"}] * 2]})
    check = sim.state.suggested[0].check
    assert check is not None
    preview = check_preview(sim.state, RULES.data, check)
    apply_tool(sim, "request_check", check)
    rolled = next(p for t, p in sim.events if t == "check_resolved")
    assert preview.chance == rolled["chance"]
    json.dumps(check)  # The check is stored in the event log, so it must be plain data.


def test_d033_action_labels_stay_brief() -> None:
    long = {"label": "Bargain with the god and ask what the dead man can tell you if you speak now"}
    sim = sworn()
    assert not apply_tool(sim, "suggest_actions", {"actions": [GOOD, long, {"label": "Run"}]}).accepted


def test_d031_oath_choices_are_filtered_from_suggestions_until_the_offer_is_answered() -> None:
    actions = [{"label": "Swear to Veshra", "cost": "a Burden"}, {"label": "Ask why"}, {"label": "Hide"}]
    sim = fresh()
    assert apply_tool(sim, "suggest_actions", {"actions": actions}).accepted
    assert [a.label for a in sim.state.suggested] == ["Ask why", "Hide"]
    after = sworn()
    assert apply_tool(after, "suggest_actions", {"actions": actions}).accepted
    assert len(after.state.suggested) == 3


def test_d031_narrator_hooks_and_standing_have_a_turn_limit() -> None:
    sim = sworn()  # The engine's own opening hooks do not spend the allowance.
    for number in range(2):
        assert apply_tool(
            sim, "register_hook", {"description": f"h{number}", "due_condition": "later"}
        ).accepted
    assert not apply_tool(sim, "register_hook", {"description": "h9", "due_condition": "later"}).accepted
    args = {"entity": "kaul", "kind": "slight", "direction": "+", "witness": "npc:a", "reason": "x"}
    assert apply_tool(sim, "adjust_standing", args).accepted
    assert apply_tool(sim, "adjust_standing", args).accepted
    assert not apply_tool(sim, "adjust_standing", args).accepted


def test_d031_healing_needs_a_wound() -> None:
    assert not apply_tool(sworn(), "apply_effect", {"kind": "heal", "source": "rest", "reason": "x"}).accepted


def test_commands_reject_bad_choices() -> None:
    sim = fresh()
    with pytest.raises(Rejected):
        choose_class(sim, "warden")  # not yet sworn
    with pytest.raises(Rejected):
        choose_profession(sim, "smith")
    resolve_offer(sim, "drovash")
    with pytest.raises(Rejected):
        choose_class(sim, "nobody")
    with pytest.raises(Rejected):
        choose_profession(sim, "nobody")
    sim.state.free_points = 1
    with pytest.raises(Rejected):
        allocate_point(sim, "luck")


def test_tool_definitions_have_no_refs_for_small_models() -> None:
    text = json.dumps(tool_definitions())
    assert "$ref" not in text and "$defs" not in text
    assert (
        tool_definition("suggest_actions")["input_schema"]["properties"]["actions"]["items"]["type"]
        == "object"
    )


def test_unknown_event_is_an_error() -> None:
    with pytest.raises(ValueError, match="unknown event"):
        replay([("from_the_future", {})])


TOOL_CALLS = st.one_of(
    st.fixed_dictionaries(
        {
            "name": st.just("request_check"),
            "args": st.fixed_dictionaries(
                {
                    "stat": st.sampled_from(sorted(STATS)),
                    "difficulty": st.sampled_from(["routine", "hard", "severe", "heroic"]),
                    "challenge_tier": st.integers(0, 8),
                    "approach": st.sampled_from(["force", "other"]),
                }
            ),
        }
    ),
    st.just({"name": "apply_effect", "args": {"kind": "damage", "source": "c1", "reason": "x"}}),
    st.just({"name": "apply_effect", "args": {"kind": "damage", "source": "hazard:fire", "reason": "x"}}),
    st.just({"name": "apply_effect", "args": {"kind": "heal", "source": "aid:friend", "reason": "x"}}),
    st.just({"name": "grant_xp", "args": {"kind": "major", "reason": "x"}}),
    st.just({"name": "grant_xp", "args": {"kind": "milestone", "reason": "x"}}),
    st.builds(
        lambda kind, direction: {
            "name": "adjust_standing",
            "args": {
                "entity": "kaul",
                "kind": kind,
                "direction": direction,
                "witness": "npc:a",
                "reason": "x",
            },
        },
        st.sampled_from(["slight", "notable", "grave"]),
        st.sampled_from(["+", "-"]),
    ),
    st.just({"name": "nonsense", "args": {}}),
    st.just({"name": "new_turn", "args": {}}),
)


def play(sim: Simulation, calls: list[dict[str, Any]]) -> Iterator[Simulation]:
    for call in calls:
        if call["name"] == "new_turn":
            carried = sim.events
            sim = next_turn(sim)
            sim.events = carried
        else:
            apply_tool(sim, call["name"], call["args"])
        yield sim


@settings(max_examples=60, deadline=None)
@given(seed=st.integers(1, 10_000), calls=st.lists(TOOL_CALLS, max_size=40))
def test_eng06_replay_of_any_action_sequence_equals_live_state_and_bounds_hold(
    seed: int, calls: list[dict[str, Any]]
) -> None:
    sim = sworn(seed)
    for sim in play(sim, calls):  # noqa: B020
        state = sim.state
        assert 0 <= state.wounds <= state.max_hp
        assert not state.downed or state.hp == 0
        assert all(-100 <= v <= 100 for v in state.standing.values())
        assert state.xp >= 0
    # Events go through JSON, as they do in the database.
    stored = json.loads(json.dumps(sim.events))
    assert replay((t, p) for t, p in stored) == sim.state
