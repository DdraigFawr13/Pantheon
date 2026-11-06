# M2c Story tools

- **Status:** Draft, checked (paraphrase, critic and zero-decision passes on 2026-11-06; findings sorted below)
- **Planned in:** M2 round 1 (https://claude.ai/artifact/S1M8kTeHdi6pX1njM7FXvA), review and round 2 (https://claude.ai/artifact/LcHA2Zu4vbVaX4jYuhdBEP), D-052 (3). **Decisions:** D-029 (the player swears by command), D-013 (petitions through Vessels; witnesses), D-038 (clocks and petitions), D-048 (a due thread gets one way back), D-052 (3). The assumptions A1 to A10 below become D-055 on approval.

**Terms.** *Scribe step*: the third step of a turn, after the prose, where the narrator records consequences through tools (D-031; `turn_tools` in `src/pantheon/narrator/loop.py`). *Dual Offer*: the opening's two Oath offers, settled by the player command `resolve_offer`. *Downed*: HP 0 in a fight. *Counted day*: days since the start of play without Blank Days, `counted_days(state.day)` in `engine/calendar.py` (D-038). *Journal tab*: the Pantheon Table page's second tab (`docs/play/pantheon-table.html`, `renderJournal`). *NAR-04*: prose never states a number the engine did not return. *G-nn*: a canon gap in `docs/canon_gaps.md`; *D-nn*: an entry in `docs/DECISIONS.md`.

## Problem

From `docs/BUILD_PLAN.md` M2c and D-052 (3): the narrator may invent people and places ("register the invention with `introduce_npc`, `introduce_location`", `prompts/narrator.md:15`), may test an Oath's Burden, may offer a second Oath and may move a global clock, but none of those tools exists. `_TOOLS` in `src/pantheon/engine/tools.py` has no `introduce_npc`, `introduce_location`, `offer_oath`, `test_burden` or `advance_clock` (searched: `grep -rn introduce_npc src/` finds only the prompt), and `apply_tool` rejects an unknown tool, so today the invention is simply lost: a new NPC lives only in the prose, the next turn's prompt does not list it, a Burden is never tested, the only Oath a character can hold is the opening one, and a clock moves only with the season (`engine/calendar.py`, `_season_turns`). The owner's playtest (`docs/playtests/2026-11-06-session-play.md`) already has an invented Rifter, Tam, whom the engine does not know.

## Goals

- The narrator registers each invented person and place through a tool, the engine keeps them as state (ENG-06), the next prompt lists them so the story reuses them, and the player can see them on the game page and in the chronicle (GAME-04).
- A god may offer an Oath after the opening, by the engine's rules on slots and Standing; only the player swears or refuses it, by command on both paths (D-029).
- The narrator may say a Burden was tested; `kept: false` applies the Breach from `world/power_tiers.md:141` (blessing suspended, Standing with the god -20) and the god sets an atonement task as a petition (D-013 (3)); granting it restores the Oath, and a lapsed or refused atonement can be offered again.
- `advance_clock` moves a clock one segment only for a cause the clock's data ties to it, at most once per clock per season by story, so "only when the story supports it" (`world/factions.md:78`) is a rule the engine checks, and D-014's pace (one segment a season, `_season_turns`) is at most doubled, never swamped.
- Every new rule is an event the Ledger shows (`ledger_lines`) and the page renders; no number appears that the engine did not return (NAR-04).

## Non-goals

- No memory or retrieval: known people and places go into the prompt as a short list (the last 12, like hooks); FTS5 and summaries are M3 (MEM-02, MEM-03).
- No second or third Oath per god: `world/data/oaths.yaml` holds one Oath per god (G-20), so a later Oath is always from a god not yet sworn.
- No Oath for the Unwritten (a character who refused both opening Oaths): whether they may swear later is canon (G-37, new); `offer_oath` is rejected for them.
- No Oath conflicts (`resolve_oath_conflict` is a later player command, D-052 (6)) and no perk mechanics: Oath perks are prose until G-14 settles check categories, so a Breach suspends the perk in words and the Standing in numbers (Open question 1).
- No engine-checked Burdens: the Turning Tide's 30 days could be checked by the calendar, but D-038 (11) defers Oath timers; `test_burden` is the narrator's judgement, as `docs/architecture.md` section 6 says (Open question 2).
- No beats: `beat:<clock_id>` causes are listed in data and refused by `advance_clock` until M2d adds `record_beat`.
- No NPC stats, pools or foe entries: a fight with a known NPC still goes through `start_fight` with its own `foes`. No character location: where the character is becomes state later (G-36, new).
- No change to the Dual Offer (`resolve_offer`) or to Trials.

## Journeys and checks

Each check is a new test, named with its requirement ID, in `tests/engine/test_story_tools.py` unless another file is named. Each fails at commit `4369b12` for the reason given; where part of a check already holds, that part is marked.

### J1 A new person enters the story and stays

- **Given** a sworn character, scribe step
- **When** the narrator calls `introduce_npc` with `name: "Tam"`, `role: "rifter"`, `tier: 1`, `disposition: "wary"`
- **Then** the call is accepted, one `npc_introduced` event is recorded, `state.npcs` holds Tam with the turn number, the Ledger line reads "Met: Tam, rifter (Tier 1, wary)", the next turn's prompt lists "Tam, rifter, Tier 1, wary (turn N)" under "Known people", and `session screen` has a `cast` list the Journal tab renders. **Check:** `test_eng02_introduce_npc_records_and_shows_the_person`; `test_prompt_lists_known_people_and_places` (`tests/narrator/test_loop.py`); `test_session_screen_cast_and_places` (`tests/test_session.py`). Fail now: the tool is unknown, `state.npcs` does not exist.

### J2 The engine refuses what canon forbids about people

- **Given** Tam is known
- **When** the narrator calls `introduce_npc` for "tam" again, for "Tam the Rifter", for "Dunmore", for a Tier 4 stranger, then for a third new person in one turn
- **Then** each is rejected with its reason: "Tam is already known", "Tam is already known" (a whole-word prefix), "Hale Dunmore is already known (regions.yaml notables)", "nobody above Tier 3 lives in The Ford Reaches (regions.yaml)", "at most 2 people a turn"; nothing is recorded. **Check:** `test_eng02_introduce_npc_rejects_duplicates_tier_above_the_cap_and_a_third_a_turn`

### J3 A place is named once

- **Given** the same setup
- **When** the narrator calls `introduce_location` with `name: "The Drowned Cellar"`, `region: "ford_reaches"`, `description: "…"`, then again for "Cinder Ford", then a second new place in the same turn
- **Then** the first is accepted (`location_introduced`; Ledger "Found: The Drowned Cellar (The Ford Reaches)"; the prompt lists it under "Known places"); "Cinder Ford" is rejected: "Cinder Ford is already on the map (regions.yaml)"; an unknown `region` and the second new place in a turn are rejected. **Check:** `test_eng02_introduce_location_records_once_and_knows_the_map`

### J4 A god offers a second Oath; only the player answers

- **Given** a Tier 2 character sworn to Ysmere, no Standing entry for Kaul (read as 0)
- **When** the scribe calls `offer_oath` with `god: kaul`, `oath_id: held_line`
- **Then** `oath_offered` is recorded and `state.offers == ["held_line"]`; the Ledger reads "Kaul offers the Held Line"; the status menu, the page and `pantheon play` show the offer with its gift and burden; `session swear held_line` records `oath_sworn` (affinity iron to its current rank +1, `level` unchanged), empties `offers`, and registers the hook "Kaul's answer to the Oath"; `session refuse held_line` instead records `oath_refused`, empties `offers`, and registers "Kaul's response to being refused". Rejected, with nothing recorded: at Tier 1 (slots full), for Ysmere (already sworn), for `oath_id: open_hand` with `god: kaul` (not Kaul's), with Standing with Kaul at -1, with an offer already open, and for an Unwritten character. The narrator has no tool that swears: `tool_definitions()` names none. **Check:** `test_eng02_offer_oath_rules`; `test_eng02_the_narrator_cannot_swear_a_later_oath`; `test_session_swear_and_refuse_a_later_oath_D_029` (`tests/test_session.py`); `test_play_swear_a_later_oath_from_the_menu` (`tests/test_play.py`). Fail now: no tool, no commands; `offer_choices` returns nothing after the opening.

### J5 A Burden tested, kept or broken, and atoned

- **Given** a character sworn to Ysmere (Turning Tide: "Shall not remain in one place longer than 30 days")
- **When** the scribe calls `test_burden` with `oath_id: turning_tide`, `situation: "Stayed in Cinder Ford a second month to nurse Tam"`, `kept: false`
- **Then** these events are recorded in this order: `burden_tested`, `oath_breached`, `standing_changed` (Ysmere, -20 from `rewards.oath.breach_standing`), `hook_registered` (a petition from Ysmere, `atones: turning_tide`, description "Atone for breaking the Turning Tide (turn N): a task Ysmere sets", deadline `state.day + rewards.oath.atonement_days`); `state.breached == ["turning_tide"]`; the sheet shows "Oaths: Turning Tide (breached)"; the Ledger reads "Breach: Turning Tide. Stayed in Cinder Ford a second month to nurse Tam" and, on its own line from `standing_changed`, "Standing with ysmere: -20, now …". A later `resolve_petition` on that hook with `granted: true` records `oath_restored` and the sheet drops "(breached)". With `granted: false`, or when the deadline lapses (`_lapse_petitions`), the Oath stays breached and `send_petition` with `atones: turning_tide` opens a new atonement. `kept: true` records only `burden_tested`. Rejected, with nothing recorded: a second test of the same Oath in one turn, an Oath not sworn, `kept: false` on an Oath already breached, and a Breach when `adjust_standing` has already been called twice this turn (`MAX_STANDING_PER_TURN`). **Check:** `test_eng02_test_burden_breach_costs_standing_and_sets_an_atonement_petition`; `test_eng02_test_burden_kept_records_only_the_test`; `test_eng02_atonement_restores_the_oath_and_can_be_offered_again`

### J6 A clock moves only for a cause its data ties to it, once a season

- **Given** `world/data/clocks.yaml` lists `causes` per clock (the canon round below), The Grain War at 2 of 6, and a turn in which `adjust_standing` changed Standing with `ironmarch` with a witness
- **When** the scribe calls `advance_clock` with `clock_id: grain_war`, `cause: "standing:ironmarch"`, `reason: "…"`
- **Then** it is accepted because `standing:ironmarch` is among The Grain War's causes: `clock_advanced` (value 3, `filled: false`, `neglected: false`) and `clock_engaged` for today are recorded, and the existing Ledger line reads "The Grain War moves: 3 of 6" (that line already prints for `clock_advanced`; the tool is what fails now). Rejected, with nothing recorded: a cause the clock does not list (`standing:hale` for The Lantern's Price), a `standing:` entity with no `standing_changed` event this turn, any `beat:` cause (M2d), a filled clock, a second story advance of the same clock within `SEASON_DAYS` (90 counted days), and a clock already engaged or advanced today. **Check:** `test_eng02_advance_clock_accepts_only_tied_causes_once_a_season`; `test_eng02_advance_clock_fills_and_stops`

### J7 The tools exist only at the scribe step

- **Given** any turn
- **When** `turn_tools` is asked before the prose, during a fight while Downed, or before the Dual Offer is resolved
- **Then** none of the slice's tools is offered (this half holds today); after the prose they are, on both paths (`offered` in `ui/cli/session.py` uses `turn_tools`; this half fails now). **Check:** one test per slice: `test_d031_people_and_places_are_scribe_tools_only`, `test_d031_oath_tools_are_scribe_tools_only`, `test_d031_advance_clock_is_a_scribe_tool_only`

### J8 Canon data agrees with the prose

- **Given** `world/data/regions.yaml` (new) and the `causes` in `clocks.yaml`
- **When** the loader tests run
- **Then** every row of the Regions and Key locations tables in `world/geography.md` (parsed as the clocks test parses `factions.md`: the Markdown table rows by `|`) is in `regions.yaml` with the same name; `ford_reaches` has `tier_cap: 3`; every clock has at least one cause; every cause is `standing:<id>` with an id among the gods and the faction Standing keys, or `beat:<its own clock id>`. **Check:** `test_regions_match_geography` (`tests/world/test_loader.py`); `test_clock_causes_are_tied_and_known` (beside the clocks test in `tests/engine/test_calendar.py`)

### J9 A narrator flag opens when its NPC exists

- **Given** `met_drovash_vessel` in `world/data/flags.yaml` ("only after an npc_introduced event whose role is vessel:drovash")
- **When** the narrator calls `set_flag met_drovash_vessel` before and after `introduce_npc` with `role: "vessel:drovash"`
- **Then** the first is rejected ("needs a known person with role vessel:drovash") and the second is accepted. `prophecy_bought` stays rejected (its rule needs a coin spend check that is not built). **Check:** `test_d024_met_drovash_vessel_opens_after_the_vessel_is_introduced`. Fails now: every registered narrator flag is rejected (D-030 (6)).

## Decisions

- The five tools are scribe tools (D-031): `SCRIBE_TOOLS` in `narrator/loop.py` grows; `turn_tools` needs no other change.
- Only the player swears or refuses (D-029): `offer_oath` records an offer; `swear` and `refuse` are player commands on both paths.
- Clocks: a story advance needs a cause tied to the clock in its data, once per clock per season (`SEASON_DAYS`), and counts as engaging the clock (D-038 (6) day rule reused).
- Breach: Standing -20 and "blessing suspended" shown; the atonement is a petition (D-013 (3), D-038) with an `atones` field, so `resolve_petition` restores and `send_petition` can re-offer.
- Every tool validates and counts before its first `emit`, so a rejection records nothing (ENG-02). Engine-made hooks set `sim.exempt_from_limits` in a `try/finally`.
- Canon data lands one `canon:` commit per slice (the loader is strict: an unknown field fails the load), each for the owner's approval (WLD-03).

**Assumptions** (labelled in the text; D-055 on approval):

- A1 The only region tier cap is the Ford Reaches' 3 (`world/geography.md:48`). The factions' "Highest tier present" lines are faction facts, not caps, so other regions carry no cap.
- A2 The clock causes in the canon round below are the proposal; the owner's round sets them.
- A3 `atonement_days: 90`, a season, so a Breach is not forgotten by `_lapse_petitions` in the petition's 7 days.
- A4 Until the character's whereabouts are state (G-36), `introduce_npc` applies the Ford Reaches cap to every call, and takes no `region` argument.
- A5 Oath slots by tier from D-010 live as data `rewards.oath.slots: {1: 1, 2: 2, 4: 3, 6: 4}`; a tier between thresholds takes the last threshold reached (Tier 3: 2, Tier 5: 3). Sworn Oaths, breached or not, fill slots. D-010 gains a pointer to the data (SRC-01).
- A6 A god offers only when Standing with it is 0 or more (`state.standing.get(god, 0)`).
- A7 `Hook.atones: str | None` names the Oath an atonement petition restores; no description matching.
- A8 A later Oath adds 1 to the affinity's current rank, with no cap (the opening's cap of 2 is the opening's).
- A9 An unanswered later offer lapses after `rewards.oath.offer_days: 30`, recorded as `oath_refused` with `reason: "left unanswered"` by `pass_time`, so one god's silence does not block every other offer for ever.
- A10 Duplicate names: two names are the same when their normalised forms (lower case, punctuation stripped, spaces collapsed) are equal or one is a whole-word prefix of the other.

## Alternatives rejected

- **Free-text NPC and place notes in `register_hook`**: rejected because hooks are consequences, not a cast list; the prompt would mix them and a duplicate could never be refused. It fails when the narrator names the same Rifter three ways.
- **A full canon cast file for `introduce_npc` to check against**: rejected because canon names only Dunmore and the caravan-master (`world/protagonist_seed.md:56`) and a cast is M3.5 content. Kept instead: a `notables` list in `regions.yaml` with the people canon already names.
- **`advance_clock` with check or fight outcomes as causes** (the first draft): rejected because a failed check about anything would move The Rift Tide, which is the failure "only when the story supports it" forbids, and `fight_ended` results (`victory`, `fled`, `story`, `death`, `reckoning`) name no faction. It fails after a tavern argument. Standing changes name an entity, so they can be tied to a clock.
- **A region argument or a "last location" default for `introduce_npc`**: rejected because either lets the narrator pass a Tier 4 into Cinder Ford by naming another region. It fails the first time the narrator wants a stronger foe. The cap is one number until the character's region is state (G-36).
- **Suspending the Oath's +1 affinity rank on a Breach by emitting a lower rank**: rejected because a rank already spent on a skill would leave the sheet inconsistent, and canon does not say what suspension does to skills learned. Open question 1.
- **Letting the narrator swear with `offer_oath` plus an `accepted` flag**: rejected by D-029: the first live run swore for the player.
- **A Breach that the player confirms by command**: not chosen; `docs/architecture.md` section 6 makes `test_burden` the narrator's judgement with the situation recorded. Open question 2 puts the alternative to the owner.
- **Waiting for M2d's beats before `advance_clock`**: not chosen; D-052 (3) places it in M2c, and Standing causes work without beats. S3 is the last slice so it can slide to M2d if the owner prefers.

## Risks

- The narrator introduces people it never reuses → the prompt lists the last 12 and the page shows them; `prompts/narrator.md` gains "reuse a known person or place before inventing one". Measured in the owner's playtest after M2d.
- A Breach called on a thin reading of the Burden → `situation` is kept in the event and shown in the Ledger line and the Journal (GAME-04); one test per Oath per turn; the atonement petition and `send_petition atones` keep it recoverable. The narrator is never forced to call `test_burden`, so a kept Burden costs nothing and a broken one depends on the narrator noticing; Open question 2.
- The clock causes are the wrong set → they are data; the owner's canon round sets them and play tunes them (G-08 style). The season cap bounds the damage of a wrong set.
- An open atonement is a god's one open petition (`_send_petition`), so that god sends no other petition until it closes → accepted; the atonement is the god's ask.
- "2 people a turn" blocks a market scene → the engine returns the reason; the narrator names the rest in prose and introduces them next turn.

## Design

### Data (canon, one `canon:` commit per slice, WLD-03)

- S1, `world/data/regions.yaml` (new, transcribed from `world/geography.md` Regions and Key locations): `regions: [{id, name, tier_cap: int | null}]` with ids `hale_plains`, `ironmarch_hills`, `southern_coast`, `antler_wilds`, `barrow_lands`, `candle_peaks`, `ford_reaches` (`tier_cap: 3`, A1); `places: [{id, name, region}]` for the 13 key locations (The Long Wall's region is "Hale-Ironmarch border" in the table: it goes under `hale_plains` with a comment, and G-36 asks); `notables: [{name, role, tier}]` with `Hale Dunmore, Tallyhouse Registrar, 3` (`world/geography.md:48`). Schema classes `Region`, `Place`, `Notable`, `Regions` in `world/schemas.py` (strict, like `Clock`), `GameData.regions`, loaded by `world/loader.py` like `clocks`. `world/data/README.md` lists it. `flags.yaml`: `met_drovash_vessel` gains `needs_npc_role: vessel:drovash` (`Flag.needs_npc_role: str | None`).
- S2, `world/data/rewards.yaml`: `oath: {breach_standing: 20, atonement_days: 90, offer_days: 30, slots: {1: 1, 2: 2, 4: 3, 6: 4}}` (20 from `world/power_tiers.md:141`; the rest A3, A5, A9). Schema `OathRewards` on `Rewards.oath`.
- S3, `world/data/clocks.yaml`: each clock gains `causes: [<cause>, …]`, `Clock.causes: tuple[str, ...]` with at least one entry, each `standing:<id>` (a god id or a faction Standing key: `hale`, `tallyhouse`, `convent`, `lantern`, `harbors`, `underlanes`, `ironmarch`, `wilds` as `world/factions.md` names them; the validator in `world/schemas.py` holds the list as `STANDING_ENTITIES`) or `beat:<this clock's id>`. Proposed (A2, the owner's call): `seat_vote: [standing:hale, standing:tallyhouse, standing:veshra, beat:seat_vote]`; `rift_tide: [standing:tallyhouse, beat:rift_tide]`; `grain_war: [standing:hale, standing:ironmarch, standing:kaul, beat:grain_war]`; `ember_fever: [standing:convent, standing:maru_ghen, beat:ember_fever]`; `lanterns_price: [standing:lantern, standing:ilvane, beat:lanterns_price]`.

### State and events (`engine/state.py`)

- `class Npc(BaseModel)`: `id` (the normalised name with spaces as underscores), `name`, `role`, `tier`, `disposition`, `turn`. `class Location(BaseModel)`: `id`, `name`, `region`, `description`, `turn`. `Hook` gains `atones: str | None = None`.
- `GameState` gains `npcs: list[Npc]`, `locations: list[Location]`, `breached: list[str]` (Oath ids), `clocks_story_advanced: dict[str, int]` (clock id to counted day). Old saves fold to empty; no schema change (`snapshot` rows are the model's JSON, so missing fields take defaults). The `saves` branch has 6 turns and no snapshot, so the fold changes below apply on load.
- Folds: `npc_introduced` (append), `location_introduced` (append), `oath_offered` (append, unchanged), `oath_sworn` (also removes that Oath from `offers`), `oath_refused` (`{oath, god, reason}`: remove from `offers`), `flag_set` with key `opening.dual_offer_resolved` (also empties `offers`, which held the opening's two), `burden_tested` (`{oath, god, situation, kept}`: no fold), `oath_breached` (`{oath, god, situation}`: append to `breached`), `oath_restored` (`{oath, god}`: remove), `clock_advanced` with `story: true` (also sets `clocks_story_advanced[clock]`). `oath_sworn` for a later Oath carries `level` equal to the current level (`max` keeps it).

### Tools (`engine/tools.py`; constants `MAX_NPCS_PER_TURN = 2`, `MAX_LOCATIONS_PER_TURN = 1`)

| Tool | Arguments | Rules (checked in this order, before any emit) |
|---|---|---|
| `introduce_npc` | `name` (2 to 40 chars), `role` (2 to 40; `vessel:<god id>` is the form `flags.yaml` reads), `tier` (0 to 9), `disposition` (`friendly`, `neutral`, `wary`, `hostile`) | Count (`sim.count_call("introduce_npc", MAX_NPCS_PER_TURN)`); duplicate against `state.npcs` names and `regions.notables` names (A10); `tier` above `regions.yaml` `ford_reaches.tier_cap` (A4). Emits `npc_introduced`. |
| `introduce_location` | `name` (2 to 60), `region` (a `regions.yaml` id), `description` (10 to 300) | Count (1 a turn); unknown region; duplicate against `state.locations` and `regions.places` names (A10). Emits `location_introduced`. |
| `offer_oath` | `god`, `oath_id` | `state.oaths` empty (Unwritten, or not yet sworn); `oath_id` not in data or not that god's; the god already sworn; `oath_id` in `state.oaths` or `state.breached`; `state.offers` not empty; `len(state.oaths) >= slots(state.tier)` (A5); `state.standing.get(god, 0) < 0` (A6). Emits `oath_offered {god, oath}`. |
| `test_burden` | `oath_id`, `situation` (10 to 300 chars), `kept` (bool) | Oath not in `state.oaths`; same Oath tested twice this turn (`sim.burdens_tested: set[str]`, new); `kept: false` while in `breached`; `kept: false` when `adjust_standing` is at `MAX_STANDING_PER_TURN` (counted as one call). `kept: true` emits `burden_tested`. `kept: false` emits `burden_tested`, `oath_breached`, `change_standing(god, -breach_standing, "broke the <Oath>")`, then `_add_hook` under `exempt_from_limits` (`petition_god: god`, `atones: oath_id`, `deadline_day: state.day + atonement_days`, description "Atone for breaking the <Oath> (turn N): a task <God> sets", `due_condition: "when the god's task is done"`). |
| `advance_clock` | `clock_id`, `cause` (`standing:<id>` or `beat:<id>`), `reason` (1 to 200) | Unknown clock; filled (`clock_value >= segments`); `beat:` (rejected until M2d); `cause` not in the clock's `causes`; `standing:<id>` with no `standing_changed` event for `<id>` in `sim.events` this turn; `clocks_engaged[clock] == counted_days(state.day)`; `clocks_story_advanced[clock]` within `SEASON_DAYS` of today. Emits `clock_advanced` (the `_season_turns` payload plus `story: true`, `reason`) and `clock_engaged`. |

- `send_petition` gains `atones: str | None`: accepted only for an Oath in `breached` with no open hook carrying the same `atones`; the hook carries it.
- `resolve_petition`: when the hook has `atones` and `granted` is true, also emits `oath_restored {oath, god}`.
- `set_flag`: a narrator key with `needs_npc_role` is accepted when `state.npcs` has that role, else rejected with "needs a known person with role <role>"; `Rules.flag_setters` keeps blocking the other narrator keys (D-030 (6)).
- Player commands (`engine/commands.py`): `swear_oath(sim, oath_id)` and `refuse_oath(sim, oath_id)`, for an `oath_id` in `state.offers` after the Dual Offer is resolved; both rejected in a fight. `swear_oath` emits `oath_sworn {oath, god, affinity, affinity_rank: current + 1, level: state.level}` (A8) and, under `exempt_from_limits`, a hook "<God>'s answer to the Oath" (due "within the next few days, through a Vessel or an omen", the opening's wording). `refuse_oath` emits `oath_refused {oath, god, reason: "refused"}` and the hook "<God>'s response to being refused". Lapse (A9): `pass_time` emits `oath_refused` with `reason: "left unanswered"` for an offer older than `offer_days` (`oath_offered` keeps the day: payload gains `day`).

### Narrator (`narrator/loop.py`, `narrator/assemble.py`, `prompts/narrator.md`)

- `SCRIBE_TOOLS` gains the slice's tools. `SCRIBE_PROMPT` gains one sentence each: introduce a person or place the first time it matters, and reuse known ones; `offer_oath` only when a god's Vessel or omen makes the offer in the scene and the sheet shows a free slot; `test_burden` only when the scene plainly tested a Burden, with the situation in one line; `advance_clock` only for a Standing change of this turn with a faction the clock turns on.
- `due_material`: after hooks, "Known people:" (last 12 of `state.npcs`, "name, role, Tier n, disposition (turn N)") and "Known places:" (last 12, "name, region name: description"); after clocks, "Breached: <Oath> since turn N: <situation>" for each in `breached`; for a later open offer, "Offer: <God> offers the <Oath>. Gift … Burden …" (the Dual Offer's line reused; the opening's lines stay as they are).
- `prompts/narrator.md`: line 15 names the tools that now exist; a line under Oaths and Trials on Burdens and atonement; "reuse a known person or place before inventing one".

### Screens (`ui/cli/app.py`, `ui/cli/session.py`, `docs/play/pantheon-table.html`, `ui/chronicle.py`)

- `ledger_lines`: `npc_introduced` "Met: {name}, {role} (Tier {tier}, {disposition})"; `location_introduced` "Found: {name} ({region name})"; `oath_offered` "{God} offers the {Oath}" (the opening's two show in the chronicle's prologue, which is right); `oath_refused` "Refused the {Oath}" or "The {Oath}'s offer lapsed"; `burden_tested` "Burden kept: {Oath}" or "Breach: {Oath}. {situation}"; `oath_restored` "{Oath} restored". `clock_advanced` already prints.
- `sheet`: "Oaths: Turning Tide (breached)". Nothing else.
- `session screen`: `cast: [{name, role, tier, disposition, turn}]` (not `people`: that key is the character's people, `session.py:879`), `places: [{name, region, description, turn}]`; `offers` entries gain `kind: "opening" | "later"`, later ones `{kind, id: oath_id, label, terms}`; `oath_list` entries gain `id`, `breached`, `situation`. A later offer is not in `choices_due`: it never blocks play. The page's Journal gets "People" and "Places" cards, marks a breached Oath with its situation, and its later-offer buttons send `Pantheon swear: <oath_id>` and `Pantheon refuse: <oath_id>` (the Dual Offer keeps `Pantheon choose: offer <god>`).
- `pantheon play`: `offer_choices` and `offer_terms` return the later offer as `swear:<oath_id>` and `refuse:<oath_id>` choices once the Dual Offer is resolved; the bare words `swear <oath_id>` and `refuse <oath_id>` are routed like `inspect`; before the Dual Offer is resolved `/refuse` keeps meaning "refuse both" (`app.py`, `_command`).
- Session commands `swear <oath_id>`, `refuse <oath_id>`; `.claude/hooks/play-guard.mjs` `STEPS` gains them; the `/play` skill documents them and the page comments.
- Chronicle: nothing to add; the new Ledger lines flow through `ledger_lines`.

## Slices

Each later slice rebases on the one before: all three add entries to `SCRIBE_TOOLS`, `SCRIBE_PROMPT`, `_TOOLS`, `prompts/narrator.md` and `ledger_lines`, and S1 and S2 both touch `apply_event`, `GameState`, `due_material`, `screen` and the Journal. These are line merges, not design conflicts.

### S1 People and places

- **Morgan tries:** play one turn in which the narrator meets someone; the Ledger reads "Met: …", the Journal tab shows People and Places, the next scene reuses the name; the narrator may set `met_drovash_vessel` after meeting a Vessel of Drovash.
- **Checks that fail now:** J1, J2, J3, J7 (people and places), J8 (regions), J9.
- **Files:** `world/data/regions.yaml` (new, `canon:`), `world/data/flags.yaml` (`needs_npc_role`, `canon:`), `world/data/README.md`, `src/pantheon/world/schemas.py` (`Region`, `Place`, `Notable`, `Regions`, `GameData.regions`, `Flag.needs_npc_role`), `src/pantheon/world/loader.py`, `tests/world/test_loader.py` (J8), `src/pantheon/engine/state.py` (`Npc`, `Location`, folds), `src/pantheon/engine/tools.py` (two tools, `_set_flag`, constants, `_TOOLS`), `src/pantheon/narrator/loop.py`, `src/pantheon/narrator/assemble.py`, `prompts/narrator.md`, `src/pantheon/ui/cli/app.py` (`ledger_lines`), `src/pantheon/ui/cli/session.py` (`screen`), `docs/play/pantheon-table.html` (Journal cards; republish), `tests/engine/test_story_tools.py`, `tests/narrator/test_loop.py`, `tests/test_session.py`, `docs/canon_gaps.md` (G-36, G-37).
- **Waits on:** none.

### S2 Oaths after the opening and Burdens

- **Morgan tries:** at Tier 2, a Vessel offers an Oath; the page shows Swear and Refuse with the terms; break a Burden on purpose and watch the Ledger, the sheet and the atonement petition; grant it and see the Oath restored.
- **Checks that fail now:** J4, J5, J7 (Oath tools).
- **Files:** `world/data/rewards.yaml` (`oath`, `canon:`), `src/pantheon/world/schemas.py` (`OathRewards`), `src/pantheon/engine/state.py` (`breached`, `Hook.atones`, `offers` folds), `src/pantheon/engine/tools.py` (`offer_oath`, `test_burden`, `send_petition atones`, `resolve_petition` restore), `src/pantheon/engine/commands.py` (`swear_oath`, `refuse_oath`), `src/pantheon/engine/calendar.py` (offer lapse), `src/pantheon/narrator/loop.py`, `src/pantheon/narrator/assemble.py`, `prompts/narrator.md`, `src/pantheon/ui/cli/app.py` (`ledger_lines`, `sheet`, `offer_choices`, `offer_terms`, `_command`), `src/pantheon/ui/cli/session.py` (`swear`, `refuse`, `screen`), `.claude/hooks/play-guard.mjs`, `.claude/skills/play/SKILL.md`, `docs/play/pantheon-table.html` (offer buttons, breached mark; republish), `docs/DECISIONS.md` (D-010 pointer to the slots data), tests named in J4 and J5.
- **Waits on:** S1 merged (shared lists).

### S3 Clocks with causes

- **Morgan tries:** after a witnessed Standing change with the Ironmarch, the narrator moves The Grain War and the Journal's clock gains a pip; a second try that season is refused.
- **Checks that fail now:** J6, J7 (`advance_clock`), J8 (causes).
- **Files:** `world/data/clocks.yaml` (`causes`, `canon:`), `src/pantheon/world/schemas.py` (`Clock.causes`, `STANDING_ENTITIES`), `tests/engine/test_calendar.py` (J8), `src/pantheon/engine/state.py` (`clocks_story_advanced`, fold), `src/pantheon/engine/tools.py` (`advance_clock`), `src/pantheon/narrator/loop.py`, `prompts/narrator.md`, `tests/engine/test_story_tools.py`.
- **Waits on:** S1 merged (shared lists). It may slide to M2d if the owner prefers beats to come first.

## Verification

- Every push: `node .claude/master/sync.mjs --check && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest --cov --cov-fail-under=90` (AGENTS.md).
- End to end: the M2b scripted run (`tests/test_m2b_scripted_run.py`) extended by one turn that introduces a person, offers an Oath and moves a clock on both paths; then the owner's playtest after M2d (D-052 (8)).

## Findings sorted (2026-11-06)

- Fixed: stale opening offers (fold change); clock causes tied to Standing with a season cap; atonement dead ends (`atones`, re-offer, deadline, duplicate description); region argument and default removed; duplicate names (A10, notables); `cast` key; order of checks before emit; hook-limit exemption; Unwritten rejected; slots count breached; Standing with no entry; `/refuse` meaning; offer `kind` and `oath_list.id`; `oath_offered` Ledger line; `met_drovash_vessel` work item; J6 and J7 marked for the parts that already hold; one canon commit per slice; per-slice J7 tests; terms; A1 to A10 listed.
- Contested: "the Breach skips the witness rule of D-013 (2)": D-013 (2) is about Standing for public deeds; a Breach is between the sworn and the god (`world/power_tiers.md:141`), and the architecture names `test_burden` the narrator's judgement. Open question 2 gives the owner the alternative anyway.
- Escalated: Open questions 1 to 3.
- Declined: bounding `state.npcs` (2 a turn is the bound); deriving `breached` from events (it is a fold, which is that).

## Open questions

1. What does "blessing suspended" do to the Oath's +1 affinity rank and its perk while breached? Canon (`world/power_tiers.md:141`) names the effect, not the mechanics; perks are not modelled (G-14). This spec shows the suspension and charges Standing only; G-38 for the owner.
2. Should a Breach need the player's confirmation (the narrator proposes, the player confirms by command), or stay the narrator's judgement as `docs/architecture.md` section 6 says? Recommendation: the narrator's judgement, with the situation shown; revisit after the owner's playtest if a Breach ever feels unfair.
3. Should S3 wait for M2d's beats? Recommendation: build it in M2c with Standing causes; beats add to the same data later.
