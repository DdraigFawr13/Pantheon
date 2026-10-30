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
    with timeline.transaction() as tx:                      # atomic commit (OPS-03)
        due = tx.engine.due_beats_and_hooks()               # arc beats, hooks, clocks
        prompt = narrator.assemble(tx.state, due, player_input)   # NAR-01, MEM-01
        messages = [prompt]
        for _ in range(MAX_TOOL_ROUNDS):
            reply = llm.complete(messages, tools=TOOL_SCHEMAS)
            if not reply.tool_calls:
                break
            results = [tx.engine.apply(call) for call in reply.tool_calls]  # ENG-02
            messages += [reply, results]
        tx.append_events(tx.engine.drain_events())          # ENG-06
        tx.record_turn(player_input, reply.text)
        memory.maybe_summarize(tx)                          # MEM-02
    return reply.text, tx.state.status_panel()
```

In words: the orchestrator opens a transaction, gathers due story material, assembles the prompt, then loops. Each loop iteration sends the conversation to the model. If the model requests tools, the engine applies each one and returns accept or reject results, and the loop continues. When the model returns prose with no further tool calls, the engine drains its pending events into the log, the turn is recorded, summaries are produced if a scene boundary was reached, and the transaction commits. Any exception rolls the whole turn back.

## 4. Prompt layers (fixed order)

| # | Layer | Source | Cached | Approx. budget |
|---|---|---|---|---|
| 1 | Narrator rules | `prompts/narrator.md` | Yes | 2,500 tokens |
| 2 | Canon core | `world/00_overview.md`, `power_tiers.md`, `pantheon.md` | Yes | 9,000 tokens |
| 3 | Character state | Engine snapshot (JSON) | No | 1,500 tokens |
| 4 | Chronicle | Chapter summaries, then scene summaries | No | 3,000 tokens |
| 5 | Retrieved lore and NPC dossiers | FTS5 by location, tags, names; released secrets | No | 4,000 tokens |
| 6 | Due material | Beats, hooks, clock states | No | 1,000 tokens |
| 7 | Recent turns | Last 6 turns verbatim | No | 6,000 tokens |
| 8 | Player input | Current turn | No | 500 tokens |

Layers 1 and 2 form the cache prefix. Layers 3 to 8 total approximately 16,000 tokens, within the MEM-04 target of 20,000.

## 5. Data model (SQLite)

| Table | Key columns |
|---|---|
| `timeline` | `id`, `parent_id`, `fork_turn`, `seed`, `rng_state`, `created_at` |
| `event` | `timeline_id`, `seq`, `turn`, `type`, `payload_json`, `rules_version` |
| `snapshot` | `timeline_id`, `turn`, `state_json` (every 10 turns, replay accelerator) |
| `turn` | `timeline_id`, `turn`, `player_input`, `narration`, `tokens_in`, `tokens_cached`, `tokens_out` |
| `summary` | `timeline_id`, `level` (`scene` or `chapter`), `span_start`, `span_end`, `text` |
| `hook` | `timeline_id`, `id`, `source_event`, `description`, `due_condition`, `status` |
| `lore` | `id`, `type`, `visibility`, `tags`, `reveal_gate`, `body` (FTS5 virtual table alongside) |
| `npc` | `timeline_id`, `id`, `name`, `tier`, `disposition_json`, `dossier` |

Event types (initial): `check_resolved`, `xp_gained`, `level_up`, `trial_begun`, `trial_resolved`, `oath_offered`, `oath_sworn`, `oath_breached`, `standing_changed`, `flag_set`, `item_changed`, `clock_advanced`, `npc_introduced`, `location_introduced`, `hook_registered`, `hook_resolved`, `beat_fired`.

## 6. Tool contracts (narrator to engine)

All arguments are validated by Pydantic. Unknown tools are rejected.

| Tool | Arguments | Engine behavior |
|---|---|---|
| `request_check` | `stat`, `skill?`, `base_dc` (10/15/20/25), `challenge_tier`, `stakes`, `overcome?` | Rolls per ENG-04/05; returns roll, modifiers, outcome tier |
| `apply_effect` | `target`, `kind` (`damage`/`heal`/`condition`), `amount?`, `reason` | Bounds-checks; returns new values |
| `grant_xp` | `amount`, `reason` | Engine caps per-turn XP; returns level state |
| `adjust_standing` | `entity` (god/faction/npc), `delta` (-20 to +20), `reason` | Clamps to [-100, 100] |
| `set_flag` | `key`, `value`, `reason` | Namespaced keys only |
| `register_hook` | `description`, `due_condition`, `source_choice` | Stores in consequence ledger (NAR-05) |
| `advance_clock` | `clock_id`, `segments` (1 to 2), `reason` | Rejects if clock is not narratively eligible |
| `introduce_npc` | `name`, `role`, `tier`, `disposition` | Rejects duplicates and tier above region cap |
| `introduce_location` | `name`, `region`, `description` | Registers for retrieval |
| `offer_oath` | `god`, `oath_id` | Checks prerequisites and oath conflicts |
| `begin_trial` | `kind`, `description`, `stakes` | Only legal at a tier threshold (level multiple of 10) |
| `record_beat` | `beat_id`, `outcome` | Marks an arc beat consumed |

## 7. Reveal gates

`reveal_gate` is a boolean expression over engine state, for example:

```
tier >= 3 and standing.ilvane >= 40 and flags.delves_closed >= 1
```

The evaluator shall use a restricted expression grammar (comparison, `and`, `or`, `not`, dotted state paths). No `eval`. Released secrets are recorded as events so they remain released after a fork.

## 8. Timeline forks

A fork copies events with `turn <= N` into a new `timeline` row with `parent_id` and `fork_turn`, restores the nearest earlier snapshot, replays to N, and restores the RNG state recorded at N. Fork cost is proportional to the replay distance from the nearest snapshot.

## 9. Testing strategy

| Layer | Method |
|---|---|
| Engine | Unit tests and `hypothesis` invariants: HP bounds, standing clamps, tier-delta rules, replay equivalence (state after replay equals live state) |
| Determinism | Same seed and inputs yield byte-identical event logs |
| Narrator loop | `MockClient` with recorded tool-call transcripts; assert rejection handling and retry cap |
| Prompt assembly | Golden-file tests for layer order and budget trimming |
| Secrets | Test that an unreleased secret string never appears in any assembled prompt |
| Rule adherence (eval) | Scripted scenarios run against the live model; check that prose contains no unsupplied numbers and that every significant choice produced a hook |

## 10. Cost control

- Cache the layer 1 and 2 prefix.
- Log per-turn tokens; expose a running session total in the CLI.
- Use a smaller model for summarization if quality holds in eval; keep the model identifier per task in `config.toml`.
- Enforce a hard per-session spend ceiling in config.
