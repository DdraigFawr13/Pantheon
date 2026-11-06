# Architecture

## 1. Narrative-control options

The central decision is how much of the story is authored versus improvised. Three options:

| Option | Mechanism | Strength | Weakness |
|---|---|---|---|
| A. Pure improvisation | LLM narrates freely; a state file is passed each turn | Maximum freedom; lowest build cost | Drift, forgotten threads, no long-range structure |
| B. Authored storylet graph | Hand-written scenes with preconditions (quality-based narrative) | Strong pacing and payoff; fully consistent | Authoring cost grows with scope; free text is constrained |
| C. Hybrid (selected) | Authored arc skeleton (beats with preconditions and clocks) plus LLM improvisation between beats | Long-range structure with open-ended moment-to-moment play | Requires a beat scheduler and hook ledger |

**Selected: C.** Branching emerges from state (flags, standing, clocks, oaths, tier), not from a drawn tree. An arc beat fires when its preconditions evaluate true; the narrator improvises everything between beats and is required to register hooks that later beats can consume.

## 2. Components

```
            +------------------+
 player --> |  UI (CLI / web)  |
            +---------+--------+
                      |
            +---------v--------+       +--------------------+
            |  Turn Orchestrator| <---> |  Memory            |
            +----+--------+----+       |  summaries, FTS5   |
                 |        |            +--------------------+
      tool calls |        | prompt
                 v        v
        +--------+--+   +-+------------+      +-----------+
        |  Engine   |   |  Narrator    | ---> | LLMClient |
        |  (rules,  |   |  (prompt     |      | (adapter) |
        |  events)  |   |  assembly)   |      +-----------+
        +-----+-----+   +--------------+
              |
        +-----v------+
        |  SQLite    |  events, snapshots, summaries, lore index
        +------------+
```

- **Engine**: pure Python, no network, no LLM imports. Deterministic given a seed.
- **Narrator**: builds prompts, runs the tool-call loop, validates structured output.
- **Memory**: produces and retrieves summaries and lore; enforces the token budget.
- **Orchestrator**: owns the turn transaction.

## 3. Turn loop

```python
def take_turn(timeline, player_input):
    state = timeline.state()                                 # read-only view
    sim = engine.Simulation(state, timeline.rng_state())     # uncommitted copy
    due = sim.due_beats_and_hooks()                          # arc beats, hooks, clocks
    system, messages = narrator.assemble(state, due, player_input)  # NAR-01, MEM-01
    rejections = Counter()                                   # NAR-06, per tool call
    reply = None
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            reply = llm.complete(system, messages, tools=TOOL_SCHEMAS)  # OPS-03 retries inside
            if not reply.tool_calls:
                problems = validators.prose(reply.text, sim.numbers_returned())  # NAR-04
                if not problems:
                    break
                if rejections["prose"] >= MAX_RETRIES:
                    reply = fallback.render(sim)             # NAR-07: never record invalid prose
                    break
                rejections["prose"] += 1
                messages += [reply, rejection(problems)]
                continue
            results = []
            for call in reply.tool_calls:
                if rejections[call.key] >= MAX_RETRIES:
                    results.append(dropped(call)); sim.log_failure(call)   # NAR-06
                    continue
                result = sim.apply(call)                     # ENG-02
                if result.rejected:
                    rejections[call.key] += 1
                results.append(result)
            messages += [reply, results]
        else:
            reply = llm.complete(system, messages, tools=None)  # force prose, no tools
            if validators.prose(reply.text, sim.numbers_returned()):
                reply = fallback.render(sim)                 # the forced round is checked too
    except LLMUnavailable:
        reply = fallback.render(sim)                         # NAR-07, engine text only
    with timeline.transaction() as tx:                       # short, atomic (OPS-03)
        tx.append_events(sim.drain_events())                 # ENG-06
        tx.record_turn(player_input, reply.text, fallback=reply.is_fallback)
    memory.maybe_summarize(timeline)                         # MEM-02, own transaction
    return reply.text, timeline.state().status_panel()
```

In words: the orchestrator works on an uncommitted simulation of the state, so model calls never hold a database write lock. Each loop iteration sends the conversation to the model. Tool calls are applied to the simulation; each distinct call may be rejected at most twice before it is dropped and the failure is logged. Every reply that will be recorded is checked for unsupplied numbers (NAR-04): prose that fails after the retries, and a forced-prose reply that fails, are replaced by the engine's fallback text, so invalid prose never enters the chronicle. If the round cap is reached while the model is still calling tools, one last call without tools forces prose. If the model is unavailable after OPS-03 retries, the engine renders a plain fallback turn. Only then are the events and the turn written in one short transaction; a crash before it leaves the log untouched. Summaries are produced after the commit and stored; a failed summary is retried at the next boundary.

## 4. Prompt layers (fixed order)

| # | Layer | Source | Cached | Where | Budget (ceiling) |
|---|---|---|---|---|---|
| 1 | Narrator rules | `prompts/narrator.md` | Yes | system | 2,500 tokens |
| 2 | Canon core | `world/00_overview.md`, `power_tiers.md`, `pantheon.md` | Yes | system | 9,000 tokens |
| 3 | Character state | Engine snapshot (JSON) | No | system | 1,500 tokens |
| 4 | Chronicle | Chapter summaries, then scene summaries | No | system | 3,000 tokens |
| 5 | Retrieved lore and NPC dossiers | FTS5 by location, tags, names; released secrets | No | system | 4,000 tokens |
| 6 | Due material | Beats, hooks, clock states | No | system | 1,000 tokens |
| 7 | Recent turns | Last 6 turns verbatim | No | messages | 6,000 tokens |
| 8 | Player input | Current turn | No | messages | 500 tokens |

Layers 1 and 2 form the cache prefix; the cache breakpoint sits at the end of layer 2, so every instruction (including the output format) is above it. Layers 3 to 8 total approximately 16,000 tokens, within the MEM-04 target of 20,000. Measured 2026-10-30: the layer 1 and 2 files are 23,946 bytes on disk (estimate at 4 characters per token: about 6,000 tokens, under the 11,500-token ceiling); check it against the provider's minimum cacheable prefix when the adapter is built.

## 5. Data model (SQLite)

| Table | Key columns |
|---|---|
| `meta` | `schema_version` (ENG-10; upgraders run on open, a failed upgrade aborts without writing) |
| `timeline` | `id`, `parent_id`, `fork_turn`, `seed`, `rng_state`, `rules_version`, `created_at` |
| `event` | `timeline_id`, `seq`, `turn`, `type`, `payload_json` (resolved outcome) |
| `snapshot` | `timeline_id`, `turn`, `state_json` (every 10 turns, replay accelerator) |
| `turn` | `timeline_id`, `turn`, `player_input`, `narration`, `is_fallback`, `tokens_in`, `tokens_cached`, `tokens_out` |
| `summary` | `timeline_id`, `level` (`scene` or `chapter`), `span_start`, `span_end`, `text` |
| `rng_checkpoint` | `timeline_id`, `turn`, `stream`, `state` (each RNG stream that moved in a turn, for forks; D-038) |
| `lore` | `id`, `type`, `visibility`, `tags`, `reveal_gate`, `body` (FTS5; rebuilt from `world/` on start, never written by play) |

**Source and projections.** `event` is the only source of game state (ENG-06). Hooks, NPCs, locations, clocks, flags, inventory, released secrets and the calendar are projections: rebuilt by folding events, cached in snapshots, never written directly. `turn` and `summary` are not game state but are non-reproducible text, so forks copy them (ENG-08). `created_at` is metadata only and never read by rules (ENG-11).

**Events record outcomes.** `check_resolved` stores the dice, modifiers, total and outcome; `xp_gained` stores the amount the engine set. Replay never calls the RNG. A timeline keeps the `rules_version` it was created under; changing rules affects new timelines, and old ones upgrade only through an explicit upgrader.

Event types (initial): `opening_gods_drawn`, `check_resolved`, `xp_gained`, `level_up`, `trial_begun`, `trial_resolved`, `class_evolved`, `stat_point_allocated`, `skill_offered`, `skill_learned`, `skill_used`, `skill_evolved`, `shard_absorbed`, `fragments_fused`, `affinity_raised`, `loot_granted`, `title_granted`, `profession_xp_gained`, `item_crafted`, `oath_offered`, `oath_sworn`, `oath_conflict_raised`, `oath_conflict_resolved`, `oath_breached`, `burden_tested`, `petition_resolved` (a petition is a `hook_registered` with a god and a deadline; D-038), `bounty_accepted`, `bounty_completed`, `standing_changed`, `rumour_recorded`, `flag_set`, `item_changed`, `currency_changed`, `effect_applied`, `injury_gained`, `fight_started`, `foe_hit`, `skill_spent`, `overspend_rolled`, `exchange_ended`, `fight_ended`, `level_lost`, `downed`, `last_breath`, `died`, `reckoning`, `time_advanced`, `clock_advanced`, `clock_engaged`, `npc_introduced`, `location_introduced`, `hook_registered`, `hook_resolved`, `beat_fired`, `secret_released`, `actions_suggested`, `tool_call_dropped`, `rift_closed`.

## 6. Tool contracts (narrator to engine)

All arguments are validated by Pydantic. Unknown tools are rejected. Where the narrator names a `kind`, the engine maps it to a number from its rules table (ENG-09); the tables are canon balance values (see `docs/canon_gaps.md`).

| Tool | Arguments | Engine behavior |
|---|---|---|
| `request_check` | `stat`, `skill?`, `difficulty` (`routine`/`hard`/`severe`/`heroic`), `challenge_tier`, `approach` (`force`/`other`), `stakes`, `overcome?` | Rolls d100 per ENG-04/05; ENG-05 auto-fail applies only to `approach: force`; validates the `overcome` parts it can (Standing, Artifact tier, Ally tier); returns chance, roll, outcome, `check_id` |
| `start_fight` | `foes` (`name`, `tier`, `threat`), `reason` | Begins a fight; draws each foe's intent (D-039) |
| `fight_move` | `move` (`attack`/`guard`/`flee`), `stat`, `target?`, `skill?`, `overspend?` | The player's move in one exchange. The engine sets difficulty and tier, rolls, applies hits and blows, regenerates pools and draws new intents (D-039) |
| `end_fight` | `reason` | Ends a fight for a story reason; refused for the Downed (D-039) |
| `use_skill` (not built; `fight_move` covers fights, D-039) | `skill_id`, `target?`, `overspend?` | Checks the skill is known, unblanked and off cooldown, and that the pool can pay (overspend up to 50 % if allowed); deducts the cost; rolls for Injury after an overspend; may chain a `request_check` |
| `grant_loot` | `source` (`rift_floor:<id>`, `rift_core:<id>`, `foe:<id>`, `cache:<id>`) | Rolls shards, fragments and items from the source's loot table; the narrator never picks shard rarity. `rift_core:<id>` is legal only after a successful check this turn at that rift's core tier; it emits `rift_closed` (which adds 1 to `flags.rifts_closed`) and grants the rift's title |
| `apply_effect` | `target`, `kind` (`damage`/`heal`/`condition`), `source` (`check_id` or named hazard), `reason` | Size from the source check's outcome and the effect table; bounds-checks; returns new values; HP 0 emits `downed` |
| `grant_xp` | `kind` (for example `minor`, `major`, `milestone`), `reason` | Amount from the XP table; per-turn cap; returns level state |
| `adjust_standing` | `entity` (god/faction/npc), `kind` (`slight`/`notable`/`grave`), `direction` (`+`/`-`), `witness` (`npc:<id>`/`evidence:<item>`/`record:<office>`/`none`), `reason` | Delta from the Standing table; clamps to [-100, 100]; with `witness: none` records a rumour instead (D-013) |
| `grant_title` | `title_id`, `witness`, `reason` | Validates the title's condition against state; needs a witness |
| `send_petition` | `god`, `ask`, `due_condition` | Registers a petition as a hook, from a sworn god, one open per god; passing its deadline counts as ignored and lowers Standing (D-038) |
| `resolve_petition` | `hook_id`, `granted`, `reason` | Closes an open petition and adjusts Standing; not in the turn it arrived (D-038) |
| `engage_clock` | `clock_id`, `reason` | Records that a tested deed this turn touched a clock's threads, so it is not neglected this season; once per clock per day (D-038) |
| `test_burden` | `oath_id`, `situation`, `kept` (bool) | Records the narrator's judgement; `kept: false` applies the Breach. The `burden_tested` event keeps `situation`, and the status panel and `pantheon log` show it, so the player can see why a blessing was suspended (GAME-04) |
| `adjust_inventory` | `item`, `quantity` (+/-), `reason` | Narrator chooses the item and count (ENG-09); rejects removing what is not held and counts above the per-turn bound |
| `adjust_currency` | `amount` (+/-), `reason` | Narrator chooses the amount; rejects overdraft and gains above the bound for the character's tier |
| `advance_time` | `span` (`minutes`/`hours`/`rest`/`day`/`days`), `count?`, `reason` | Advances the calendar; ticks time-driven clocks and lapses overdue petitions. `rest` also heals. Oath timers and daily Boons wait for canon rules (D-038) |
| `set_flag` | `key`, `value`, `reason` | A registered key (section 7) only when its `set_by` is `narrator` and its `accept` rule holds; any other key only under `story.` and only `true` or `false` |
| `register_hook` | `description`, `due_condition`, `source_choice` | Stores in consequence ledger (NAR-05) |
| `advance_clock` | `clock_id`, `cause` (`check_id` or `beat_id` from this turn), `reason` | One segment. Accepts only when the clock's data lists the cause's kind (for example a failed check against that faction, or a beat tagged with the clock), and at most once per clock per in-world day. This is the computable form of "only when the story supports it" (`world/factions.md`) |
| `introduce_npc` | `name`, `role`, `tier`, `disposition` | Rejects duplicates and tier above region cap |
| `introduce_location` | `name`, `region`, `description` | Registers for retrieval |
| `offer_oath` | `god`, `oath_id` | Checks prerequisites and oath conflicts |
| `resolve_oath_conflict` | `conflict_id`, `choice` (`honor:<oath>`) | Breaches the other Oath (blessing suspended, Standing -20) per `world/power_tiers.md` |
| `begin_trial` | `kind`, `description`, `witness`, `stakes` | Only legal at a tier threshold (level multiple of 10) |
| `resolve_trial` | `trial_id` | Outcome (Ascend, Setback, Breaking) from the trial's recorded checks, not from the narrator; Ascend unlocks the player's evolution choice |
| `mark_hostile_exchange` (replaced: the engine adds a mark each turn in a fight while Downed, D-039) | `reason` | While Downed, adds a Last Breath mark; three marks is death or Reckoning per config |
| `record_beat` | `beat_id`, `outcome` | Marks an arc beat consumed |
| `suggest_actions` | `actions`: 3 to 4 of `{label, violent: bool, cost: str?, tag: str?}` | Rejects sets without a non-violent action and an action with a cost (NAR-03), and tags the character does not have (D-033); the UI renders them |

### Player commands (UI to engine, no narrator)

Choices that belong to the player go straight from the UI to the engine and are logged as events like any other: `allocate_point(stat)`, `pick_skill(offer_id, choice)`, `absorb_shard(shard_id, target_skill?)`, `fuse_fragments(kind)`, `choose_evolution(option_id)`, `craft(recipe_id, inputs)`, `choose_class` and `choose_profession` at awakening. The narrator learns the result through the state snapshot.

## 7. Reveal gates

`reveal_gate` is a boolean expression over engine state, for example:

```
tier >= 3 and standing.ilvane >= 40 and flags.rifts_closed >= 1
```

The evaluator shall use a restricted expression grammar (comparison, `and`, `or`, `not`, parentheses, dotted state paths; a bare path is true when its value is set and truthy). No `eval`. Released secrets are recorded as `secret_released` events so they remain released after a fork.

**Flag registry.** A gate may read only state fields (`tier`, `level`, `standing.<id>`, where a god's id is its name in lower case with `_` for `-`, for example `ilvane`, `maru_ghen`) and flags listed in `world/data/flags.yaml` or `world/sealed/data/flags.yaml` (D-024). Each entry gives the flag's `kind` (`bool` or `counter`), who sets it (`engine`, `beat` or `narrator`) and, for narrator flags, an `accept` rule the engine checks. Counters only go up. The M0 test fails on a gate path that is in neither list, so no gate depends on a flag nothing sets.

## 8. Timeline forks

A fork creates a new `timeline` row with `parent_id` and `fork_turn`, copies events, `turn` rows, snapshots and `rng_checkpoint` rows with `turn <= N` and `summary` rows with `span_end <= N`, and sets the RNG state recorded at N. Loading it restores the nearest earlier snapshot and replays to N, so cost is proportional to the replay distance from that snapshot. Player commands after turn N are stamped N + 1, so a fork at N does not include them. A save that recorded no RNG state at N refuses the fork (D-038).

## 9. Testing strategy

| Layer | Method |
|---|---|
| Engine | Unit tests; `hypothesis` generates action sequences for invariants: HP bounds, standing clamps, tier-delta rules, replay equivalence (state after replay equals live state) |
| Determinism | One fixed-seed test: same seed and inputs yield byte-identical event logs (GAME-06) |
| Boundaries | A pytest walks imports under `engine/` and fails on `narrator`, `llm` or `ui` |
| Narrator loop | `MockClient` with recorded tool-call transcripts; assert rejection handling, retry cap, forced-prose round and fallback turn |
| Prose validator | Unit tests for NAR-04: digits and number words not returned by the engine this turn are rejected |
| Prompt assembly | Golden-file tests for layer order, cache breakpoint position and budget trimming |
| Secrets | Test that an unreleased secret string never appears in any assembled prompt |
| Rule adherence (eval) | Scripted scenarios run against the live model; check that every significant choice produced a hook and the prose validator rarely fires |

## 10. Cost control

- Cache the layer 1 and 2 prefix.
- Log per-turn tokens; expose a running session total in the CLI.
- Use a smaller model for summarization if quality holds in eval; keep the model identifier per task in `config.toml`.
- Enforce a hard per-session spend ceiling in config, priced from the `[pricing]` table (per million input, cached and output tokens per model).
