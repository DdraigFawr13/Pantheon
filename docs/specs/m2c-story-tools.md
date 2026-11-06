# M2c Story tools

- **Status:** Draft
- **Planned in:** M2 round 1 (https://claude.ai/artifact/S1M8kTeHdi6pX1njM7FXvA), review and round 2 (https://claude.ai/artifact/LcHA2Zu4vbVaX4jYuhdBEP), D-052 (3). **Decisions:** D-029 (the player swears by command), D-013 (petitions through Vessels), D-038 (clocks and petitions), D-048 (a due thread gets one way back), D-052 (3). This spec's assumptions become one DECISIONS entry on approval.

## Problem

From `docs/BUILD_PLAN.md` M2c and D-052 (3): the narrator may invent people and places ("register the invention with `introduce_npc`, `introduce_location`", `prompts/narrator.md:15`), may test an Oath's Burden, may offer a second Oath and may move a global clock, but none of those tools exists. `_TOOLS` in `src/pantheon/engine/tools.py` has no `introduce_npc`, `introduce_location`, `offer_oath`, `test_burden` or `advance_clock` (searched: `grep -rn introduce_npc src/` finds only the prompt). So today a new NPC lives only in the prose, the next turn's prompt does not list it, a Burden is never tested, the only Oath a character can hold is the opening one, and a clock moves only with the season (`engine/calendar.py`, `_season_turns`). The owner's playtest (`docs/playtests/2026-11-06-session-play.md`) already has an invented Rifter, Tam, whom the engine does not know.

## Goals

- The narrator registers each invented person and place through a tool, the engine keeps them as state (ENG-06), the next prompt lists them so the story reuses them, and the player can see them on the game page and in the chronicle (GAME-04).
- A god may offer an Oath after the opening, by the engine's rules on slots and Standing; only the player swears or refuses it, by command on both paths (D-029).
- The narrator may say a Burden was tested; `kept: false` applies the Breach from `world/power_tiers.md:141` (blessing suspended, Standing with the god -20) and the god sets an atonement task as a petition (D-013 (3)); granting it restores the Oath.
- `advance_clock` moves a clock one segment only for a cause the clock's data allows, at most once per clock per counted day, so "only when the story supports it" (`world/factions.md:78`) is a rule the engine checks, not a hope.
- Every new rule is an event the Ledger shows (`ledger_lines`) and the page renders; no number appears that the engine did not return (NAR-04).

## Non-goals

- No memory or retrieval: known people and places go into the prompt as a short list (the last 12, like hooks); FTS5 and summaries are M3 (MEM-02, MEM-03).
- No second or third Oath per god: `world/data/oaths.yaml` holds one Oath per god (G-20), so a later Oath is always from a god not yet sworn.
- No Oath conflicts (`resolve_oath_conflict` is a later player command, D-052 (6)) and no perk mechanics: Oath perks are prose until G-14 settles check categories, so a Breach suspends the perk in words and the Standing in numbers (see Open questions).
- No beats: `beat:<id>` causes are accepted by `advance_clock` only once M2d adds `record_beat`; until then the data may list them and no call can supply one.
- No NPC stats, pools or foe entries: a fight with a known NPC still goes through `start_fight` with its own `foes`.
- No change to the Dual Offer (`resolve_offer`) or to Trials.

## Journeys and checks

Each check is a new test in `tests/engine/test_story_tools.py`, `tests/test_session.py` or `tests/test_play.py`, named with its requirement ID. All fail at commit `4369b12` because the tools, events, commands and data do not exist.

### J1 A new person enters the story and stays

- **Given** a sworn character in Cinder Ford, scribe step
- **When** the narrator calls `introduce_npc` with `name: "Tam"`, `role: "rifter"`, `tier: 1`, `disposition: "wary"`
- **Then** the call is accepted, one `npc_introduced` event is recorded, `state.npcs` holds Tam with the turn number, the Ledger line reads "Met: Tam, rifter (Tier 1, wary)", the next turn's prompt lists "Tam, rifter, Tier 1, wary (turn N)" under "Known people", and `session screen` has a `people` list the page's Journal renders. **Check:** `test_eng02_introduce_npc_records_and_shows_the_person`, `test_prompt_lists_known_people_and_places`, `test_session_screen_people_and_places`

### J2 The engine refuses what canon forbids about people

- **Given** Tam is known and the character is in the Ford Reaches
- **When** the narrator calls `introduce_npc` for "tam" again, then for a Tier 4 stranger, then a third new person in one turn
- **Then** each is rejected: "Tam is already known", "nobody above Tier 3 lives in The Ford Reaches (world/geography.md)", "at most 2 people a turn"; nothing is recorded. **Check:** `test_eng02_introduce_npc_rejects_duplicates_tier_above_region_cap_and_a_third_a_turn`

### J3 A place is named once

- **Given** the same setup
- **When** the narrator calls `introduce_location` with `name: "The Drowned Cellar"`, `region: "ford_reaches"`, `description: "…"`, then calls it again for "Cinder Ford"
- **Then** the first is accepted (`location_introduced`, Ledger "Found: The Drowned Cellar (The Ford Reaches)", the prompt lists it under "Known places") and the second is rejected: "Cinder Ford is already on the map (world/geography.md)"; an unknown `region` is rejected. **Check:** `test_eng02_introduce_location_records_once_and_knows_the_map`

### J4 A god offers a second Oath; only the player answers

- **Given** a Tier 2 character sworn to Ysmere, Standing with Kaul at 0 or more
- **When** the scribe calls `offer_oath` with `god: kaul`, `oath_id: held_line`
- **Then** `oath_offered` is recorded, the Ledger reads "Kaul offers the Held Line", the menu (session `status`, page, `pantheon play`) shows the offer with its gift and burden, and `session swear held_line` records `oath_sworn` (affinity iron +1 rank, level unchanged) while `session refuse held_line` records `oath_refused` and registers a hook "Kaul's response to being refused" (the same shape as `resolve_offer`). At Tier 1 (no free slot), for a god already sworn, for an Oath not that god's, with Standing below 0, or with an offer already open, the tool is rejected and nothing is recorded. The narrator has no tool that swears. **Check:** `test_eng02_offer_oath_rules`, `test_eng02_the_narrator_cannot_swear_an_oath`, `test_session_swear_and_refuse_a_later_oath_D_029`, `test_play_swear_a_later_oath_from_the_menu`

### J5 A Burden tested, kept or broken, and atoned

- **Given** a character sworn to Ysmere (Turning Tide: "Shall not remain in one place longer than 30 days")
- **When** the scribe calls `test_burden` with `oath_id: turning_tide`, `situation: "Stayed in Cinder Ford a second month to nurse Tam"`, `kept: false`
- **Then** `burden_tested` and `oath_breached` are recorded; Standing with Ysmere falls by `rewards.oath.breach_standing` (20, `world/power_tiers.md:141`); a petition hook from Ysmere "Atone for breaking the Turning Tide: a task the god sets" with deadline `rewards.oath.atonement_days` is registered; the sheet shows "Oaths: Turning Tide (breached)"; the Ledger reads "Breach: Turning Tide. Standing with ysmere: -20". A later `resolve_petition` on that hook with `granted: true` records `oath_restored` and the sheet drops "(breached)". `kept: true` records only `burden_tested`. A second test of the same Oath in one turn, a test of an Oath not sworn, and a `kept: false` on an Oath already breached are rejected. **Check:** `test_eng02_test_burden_breach_costs_standing_and_sets_an_atonement_petition`, `test_eng02_test_burden_kept_records_only_the_test`, `test_eng02_atonement_restores_the_oath`

### J6 A clock moves only for a cause its data allows

- **Given** `world/data/clocks.yaml` lists `causes` per clock (the canon round below), and a turn whose check `c1` failed
- **When** the scribe calls `advance_clock` with `clock_id: grain_war`, `cause: "check:c1"`, `reason: "…"`
- **Then** it is accepted only if `failed_check` is among The Grain War's causes: `clock_advanced` (value +1, `filled` when it reaches its segments) and `clock_engaged` for today are recorded, and the Ledger reads "The Grain War moves: 3 of 6". With a cause kind the clock does not list, a `check:` id not rolled this turn, a filled clock, or a second call for the same clock on the same counted day, it is rejected and nothing is recorded. **Check:** `test_eng02_advance_clock_accepts_only_listed_causes_once_a_day`, `test_eng02_advance_clock_fills_and_stops`

### J7 The tools exist only at the scribe step

- **Given** any turn
- **When** `turn_tools` is asked before the prose, or during a fight while Downed, or before the Dual Offer is resolved
- **Then** none of the five tools is offered; after the prose all five are, on both paths (`offered` in `ui/cli/session.py` uses `turn_tools`). **Check:** `test_d031_story_tools_are_scribe_tools_only`

### J8 Canon data agrees with the prose

- **Given** `world/data/regions.yaml` (new) and the `causes` in `clocks.yaml`
- **When** the loader tests run
- **Then** every region and key location in `world/geography.md` is in `regions.yaml` with the same name, the Ford Reaches cap is 3, every clock has at least one cause and every cause kind is one the engine knows. **Check:** `test_regions_match_geography` (in `tests/world/test_loader.py`), `test_clock_causes_are_known_kinds` (beside the clocks test in `tests/engine/test_calendar.py`)

## Decisions

- The five tools are scribe tools (D-031): `SCRIBE_TOOLS` in `narrator/loop.py` grows by five; `turn_tools` needs no other change.
- Only the player swears or refuses (D-029): `offer_oath` records an offer; `swear` and `refuse` are player commands on both paths.
- Clocks: one segment a call, once per clock per counted day, the same day rule as `engage_clock` (D-038 (6)); an accepted advance also counts as engaging the clock for the season.
- Breach: Standing -20 and "blessing suspended" shown; the atonement is a petition (D-013 (3), D-038) so `resolve_petition` closes it.
- Canon data in one `canon:` commit for the owner: `regions.yaml`, `causes` in `clocks.yaml`, `oath` block in `rewards.yaml` (WLD-03).

The assumptions below are labelled **A1 to A9** and become D-055 on approval.

## Alternatives rejected

- **Free-text NPC and place notes in `register_hook`**: rejected because hooks are consequences, not a cast list; the prompt would mix them and a duplicate could never be refused. It fails when the narrator names the same Rifter three ways.
- **A `people.yaml` of canon NPCs for `introduce_npc` to check against**: rejected because canon names only Dunmore and the caravan-master as rescuers (`world/protagonist_seed.md:56`), and a canon cast is M3.5 content. It would fail now by being empty and later by needing a second source of truth for names already in the prose.
- **`advance_clock` with a free-text `cause`**: rejected because the engine could not check it, which is the audit's point (`world/factions.md:78` says the engine accepts only when the story supports it). It fails the first time a narrator moves The Rift Tide after a tavern argument.
- **Suspending the Oath's +1 affinity rank on a Breach by emitting a lower rank**: rejected because a rank already spent on a skill (`skill_gained`) would leave the sheet inconsistent, and canon does not say what suspension does to skills learned. It fails when a rank 2 skill sits on a rank 1 affinity. Kept as Open question 1.
- **Letting the narrator swear with `offer_oath` plus an `accepted` flag**: rejected by D-029: the first live run swore for the player.
- **One offer per turn through `suggest_actions` only**: rejected because a pending offer must outlive the turn and be visible on the page and the sheet; `state.offers` already does that for the Dual Offer.

## Risks

- The narrator introduces people it never reuses → the prompt lists the last 12 and the page shows them; the prompt rule "reuse a known person or place before inventing one" is added to `prompts/narrator.md` (Choice design). Measured in the owner's playtest after M2d.
- A Breach called on a thin reading of the Burden → `situation` is kept in the event and shown in the Ledger line and the Journal, so the owner can see why (GAME-04); the one-test-per-Oath-per-turn rule and the atonement petition keep it recoverable.
- The clock causes are the wrong set → they are data; the owner's canon round sets them and play tunes them (G-08 style).
- The cap "2 people a turn" blocks a market scene → the engine returns the reason; the narrator names the rest in prose and introduces them next turn.

## Design

### Data (canon round, one `canon:` commit, WLD-03)

- `world/data/regions.yaml` (new, transcribed from `world/geography.md` Regions and Key locations): `regions: [{id, name, tier_cap}]` and `places: [{id, name, region}]`. Caps: `ford_reaches: 3` (`world/geography.md:48`); the faction homelands take "Highest tier present" from `world/factions.md` (Hale 5, Ironmarch 5, Harbors 4, …) (**A1**: that line is the cap until canon says otherwise; listed in `docs/canon_gaps.md` as G-36). A test checks names against the prose.
- `world/data/clocks.yaml`: each clock gains `causes: [<kind>, …]`. Kinds the engine can see this turn: `failed_check`, `passed_check`, `fight_won`, `fight_lost`, `standing:<entity>` (a `standing_changed` event for that entity this turn), `beat:<clock_id>` (M2d). Proposed (**A2**, the owner's call): `seat_vote: [standing:hale, standing:tallyhouse, beat:seat_vote]`; `rift_tide: [fight_lost, failed_check, beat:rift_tide]`; `grain_war: [standing:hale, standing:ironmarch, fight_won, beat:grain_war]`; `ember_fever: [failed_check, beat:ember_fever]`; `lanterns_price: [standing:ilvane, passed_check, beat:lanterns_price]`.
- `world/data/rewards.yaml`: `oath: {breach_standing: 20, atonement_days: 90}` (20 from `world/power_tiers.md:141`; 90 is **A3**, a season, so a Breach is not forgotten by `_lapse_petitions` in a week).
- `world/data/README.md` lists the new file.

### State and events (`engine/state.py`)

- `class Npc(BaseModel)`: `id` (slug of the name), `name`, `role`, `tier`, `disposition`, `turn`. `class Location(BaseModel)`: `id`, `name`, `region`, `description`, `turn`.
- `GameState` gains `npcs: list[Npc]`, `locations: list[Location]`, `breached: list[str]` (Oath ids). Old saves fold to empty lists; no schema change (snapshots are JSON of the model, so `model_validate_json` fills defaults).
- Events and folds: `npc_introduced` (append), `location_introduced` (append), `oath_refused` (`{oath, god}`: remove from `offers`), `burden_tested` (`{oath, god, situation, kept}`: no fold), `oath_breached` (`{oath, god, situation}`: append to `breached`), `oath_restored` (`{oath, god}`: remove). `oath_offered` and `oath_sworn` keep their payloads; `oath_sworn` for a later Oath carries `level` equal to the current level.

### Tools (`engine/tools.py`)

| Tool | Arguments | Rules |
|---|---|---|
| `introduce_npc` | `name` (2 to 40 chars), `role` (2 to 40, free text; `vessel:<god>` is the form `flags.yaml` reads), `tier` (0 to 9), `disposition` (`friendly`, `neutral`, `wary`, `hostile`), `region?` | Rejected: a name already in `state.npcs` (case-insensitive); `tier` above the region's `tier_cap`; a third call in one turn (`sim.count_call("introduce_npc", 2)`). `region` defaults to the region of the last entry in `state.locations`, else `ford_reaches` (**A4**: the character's whereabouts are not state yet). |
| `introduce_location` | `name` (2 to 60), `region` (a `regions.yaml` id), `description` (10 to 300 chars) | Rejected: a name in `state.locations` or in `regions.yaml` `places` (case-insensitive); an unknown region; a second call in one turn. |
| `offer_oath` | `god`, `oath_id` | Rejected: character not sworn (`state.level == 0`); `oath_id` not that god's or not in data; the god already sworn; no free slot (slots by tier from D-010: 1 at Tier 1, 2 at Tier 2, 3 at Tier 4, 4 at Tier 6, data `oath_slots: {1: 1, 2: 2, 4: 3, 6: 4}` in `rewards.yaml` **A5**); Standing with the god below 0 (**A6**); any offer already open; the Oath already sworn or breached. Emits `oath_offered`. |
| `test_burden` | `oath_id`, `situation` (10 to 300 chars), `kept` (bool) | Rejected: Oath not sworn; same Oath tested twice in a turn; `kept: false` on an Oath in `breached`. `kept: true` emits `burden_tested`. `kept: false` emits `burden_tested`, `oath_breached`, `change_standing(god, -breach_standing)` (counted against `MAX_STANDING_PER_TURN` like a petition), and `_add_hook` for the atonement petition (`petition_god: god`, `deadline_day: state.day + atonement_days`, `description: "Atone for breaking the <Oath>: a task <God> sets"`, exempt from the hook limit like `resolve_offer`). |
| `advance_clock` | `clock_id`, `cause` (`check:<check_id>`, `fight`, `standing:<entity>`, `beat:<beat_id>`), `reason` | The cause's kind this turn: `check:<id>` → `failed_check` or `passed_check` from `sim.checks[id].outcome` (rejected if the id was not rolled this turn); `fight` → `fight_won` or `fight_lost` from this turn's `fight_ended` event; `standing:<e>` → that entity has a `standing_changed` event this turn; `beat:` rejected until M2d. Accepted only if the kind is in the clock's `causes`; rejected if filled or already advanced or engaged today (`clocks_engaged[clock] == counted_days(state.day)`). Emits `clock_advanced` (the same payload as `_season_turns`, `neglected: false`) and `clock_engaged`. |

- `resolve_petition` gains: when the hook's description starts with "Atone for breaking the" (**A7**: the hook carries `atones: <oath_id>`, a new optional `Hook` field, rather than string matching) and `granted` is true, it also emits `oath_restored`.
- Player commands (`engine/commands.py`): `swear_oath(sim, oath_id)` and `refuse_oath(sim, oath_id)` for an offer in `state.offers` after the Dual Offer is resolved; `swear_oath` emits `oath_sworn` with `affinity_rank = state.affinities.get(affinity, 0) + 1` (the opening's rule without the cap of 2 **A8**) and registers the god's answer hook; `refuse_oath` emits `oath_refused` and registers "<God>'s response to being refused". Both are rejected while a fight is on.

### Narrator (`narrator/loop.py`, `narrator/assemble.py`, `prompts/narrator.md`)

- `SCRIBE_TOOLS` += the five. `SCRIBE_PROMPT` gains one sentence each: introduce a person or place the first time it matters; `offer_oath` only when a god's Vessel or omen makes the offer in the scene and the sheet shows a free slot; `test_burden` only when the scene plainly tested a Burden, with the situation in one line; `advance_clock` only for a cause of this turn, named.
- `due_material`: after hooks, "Known people:" (last 12 of `state.npcs`, "name, role, Tier n, disposition (turn N)") and "Known places:" (last 12); after clocks, "Breached: <Oath> since turn N: <situation>" for each in `breached`; open later offers as "Offer: <God> offers the <Oath>. Gift … Burden …" (the Dual Offer's existing line, reused).
- `prompts/narrator.md`: line 15 names the tools that now exist; a line under Oaths and Trials on Burdens and atonement; "reuse a known person or place before inventing one".

### Screens (`ui/cli/app.py`, `ui/cli/session.py`, `docs/play/pantheon-table.html`, `ui/chronicle.py`)

- `ledger_lines`: `npc_introduced` "Met: {name}, {role} (Tier {tier}, {disposition})"; `location_introduced` "Found: {name} ({region name})"; `oath_offered` after the opening "{God} offers the {Oath}"; `oath_refused` "Refused the {Oath}"; `burden_tested` "Burden kept: {Oath}" or "Breach: {Oath} ({situation})"; `oath_restored` "{Oath} restored".
- `sheet`: "Oaths: Turning Tide (breached)"; after Standing, "People: n · Places: n" is not needed (the page has them).
- `session screen`: `people: [{name, role, tier, disposition, turn}]`, `places: [{name, region, description, turn}]`, `offers` comes from `offer_choices` (`ui/cli/app.py`), which returns nothing once the Dual Offer is resolved, so `offer_choices` and `offer_terms` are extended to list `state.offers` after the opening as `swear:<oath_id>` and `refuse:<oath_id>` choices with the Oath's gift and burden; `oath_list` entries gain `breached: bool` and `situation`. The page's Journal gets "People" and "Places" cards and marks a breached Oath; its offer buttons send `Pantheon swear: <oath_id>` and `Pantheon refuse: <oath_id>` after the opening (the Dual Offer keeps `Pantheon choose: offer <god>`).
- `pantheon play`: `/swear <oath_id>` and `/refuse <oath_id>` after the opening (`_settle_offer` handles the Dual Offer only today); the menu lists open offers with terms (`offer_choices` extended).
- Session commands `swear <oath_id>`, `refuse <oath_id>`; `.claude/hooks/play-guard.mjs` `STEPS` gains them; the `/play` skill documents them and the page comments.
- Chronicle: nothing to add; the new Ledger lines flow through `ledger_lines`.

## Slices

### S1 People and places

- **Morgan tries:** play one turn in which the narrator meets someone; the Ledger reads "Met: …", the Journal tab shows People and Places, the next scene reuses the name.
- **Checks that fail now:** J1, J2, J3, J7 (for the two tools), J8 (regions).
- **Files:** `world/data/regions.yaml` (new, `canon:`), `world/data/README.md`, `src/pantheon/world/schemas.py` (`Region`, `Place`, `GameData.regions`), `src/pantheon/world/loader.py` (load the file), `tests/world/test_loader.py` (J8), `src/pantheon/engine/state.py` (`Npc`, `Location`, folds), `src/pantheon/engine/tools.py` (two tools, `_TOOLS`), `src/pantheon/narrator/loop.py` (`SCRIBE_TOOLS`, `SCRIBE_PROMPT`), `src/pantheon/narrator/assemble.py` (`due_material`), `prompts/narrator.md`, `src/pantheon/ui/cli/app.py` (`ledger_lines`), `src/pantheon/ui/cli/session.py` (`screen`), `docs/play/pantheon-table.html` (Journal cards; republish), `tests/engine/test_story_tools.py`, `tests/narrator/test_loop.py` (prompt), `tests/test_session.py` (screen), `docs/canon_gaps.md` (G-36).
- **Waits on:** none.

### S2 Oaths after the opening and Burdens

- **Morgan tries:** at Tier 2, a Vessel offers an Oath; the page shows Swear and Refuse with the terms; break a Burden on purpose and watch the Ledger, the sheet and the atonement petition; grant it and see the Oath restored.
- **Checks that fail now:** J4, J5, J7 (for the two tools).
- **Files:** `world/data/rewards.yaml` (`oath` block, `oath_slots`, `canon:`), `src/pantheon/world/schemas.py` (`Rewards.oath`), `src/pantheon/engine/state.py` (`breached`, `Hook.atones`, folds), `src/pantheon/engine/tools.py` (`offer_oath`, `test_burden`, `resolve_petition` restore), `src/pantheon/engine/commands.py` (`swear_oath`, `refuse_oath`), `src/pantheon/narrator/loop.py`, `src/pantheon/narrator/assemble.py` (offers, breached), `prompts/narrator.md` (Oaths section), `src/pantheon/ui/cli/app.py` (`ledger_lines`, `sheet`, `/swear`, `/refuse`, `offer_choices`), `src/pantheon/ui/cli/session.py` (`swear`, `refuse`, `screen`), `.claude/hooks/play-guard.mjs` (`STEPS`), `.claude/skills/play/SKILL.md`, `docs/play/pantheon-table.html` (offer buttons, breached mark; republish), tests as named in J4 and J5.
- **Waits on:** none (S1's `_TOOLS` edits merge first in practice; the slices touch different functions).

### S3 Clocks with causes

- **Morgan tries:** after a failed check against the Ironmarch, the narrator moves The Grain War and the Journal's clock gains a pip; a second try the same day is refused.
- **Checks that fail now:** J6, J7 (for `advance_clock`), J8 (causes).
- **Files:** `world/data/clocks.yaml` (`causes`, `canon:`), `src/pantheon/world/schemas.py` (`Clock.causes`, kind validation), `tests/world/test_loader.py`, `src/pantheon/engine/tools.py` (`advance_clock`), `src/pantheon/narrator/loop.py`, `prompts/narrator.md`, `src/pantheon/ui/cli/app.py` (`ledger_lines` already prints `clock_advanced`), `tests/engine/test_story_tools.py`.
- **Waits on:** none.

The canon round (`regions.yaml`, `causes`, `rewards.oath`) can be one `canon:` commit at the start of S1 for the owner's approval, or one per slice.

## Verification

- Every push: `node .claude/master/sync.mjs --check && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest --cov --cov-fail-under=90` (AGENTS.md).
- End to end: the M2b scripted run (`tests/test_m2b_scripted_run.py`) extended by one turn that introduces a person, offers an Oath and moves a clock on both paths; then the owner's playtest after M2d (D-052 (8)).

## Open questions

1. What does "blessing suspended" do to the Oath's +1 affinity rank and its perk while breached? Canon (`world/power_tiers.md:141`) names the effect, not the mechanics; perks are not modelled (G-14). This spec shows the suspension and charges Standing only (**A9**); listed as G-37 for the owner.
2. Should `introduce_npc` need a witness or a check, as Standing does (D-013 (2))? Not in this spec: meeting someone is not a public deed.
