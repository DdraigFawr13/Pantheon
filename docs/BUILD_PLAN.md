# Build plan: M0 to M3.5 (first playable version)

Status: Accepted (2026-10-30; owner: "go with your recommendations"). This plan breaks the approved roadmap (`docs/roadmap.md`) into ordered tasks. The requirements live in `docs/SPEC.md`; the rules in `world/power_tiers.md`; the design decisions in `docs/DECISIONS.md` (D-001 onward). This file links to them and does not repeat them.

Session estimates are estimates (REP-01), assuming 1 session is about 2 to 3 hours of agent work.

## How each milestone runs

1. Cut a branch from the latest `main`; open a draft PR at the first reviewable checkpoint (CI-02).
2. For every ENG requirement, write the failing test first; put the requirement ID in the test name and commit message.
3. Spec'd modules go to the `implementer` agent (Sonnet) with a self-contained brief; long check runs to `test-runner`; large diffs to `reviewer`. Design and canon stay in the main session (DEL-01 to DEL-05).
4. Canon changes (`world/`) go in their own `canon:` commits for the owner to approve. Sealed changes (`world/sealed/`) go through the reviewer agent instead (WLD-04).
5. Local checks before every push: `node .claude/master/sync.mjs --check && uv run ruff check . && uv run mypy src/pantheon/engine && uv run pytest`.
6. The milestone closes with a report (requirements met, deferred, known defects), a playtest transcript in `docs/playtests/` when the narrator loop is touched, and HANDOFF and DECISIONS updated.

## Dependencies

| Package | Why | From | Status |
|---|---|---|---|
| pydantic v2, rich, pytest, pytest-cov, hypothesis, ruff, mypy | SPEC section 3 | M0 | Approved |
| fastapi | SPEC section 3 "Second UI"; needed early for the phone page (D-015); server-sent events written by hand | M2.5 | Approved |
| uvicorn | The server that runs FastAPI | M2.5 | Approved (D-019) |
| PyYAML | Parse YAML frontmatter (WLD-01) and data tables | M0 | Approved (D-019) |
| anthropic | LLM adapter for both Anthropic and Ollama (OPS-01, D-020) | M2 | Approved (D-019) |
| jinja2 | Server-rendered HTML for the phone page | M2.5 | Approved (D-019) |

HTMX loads from a pinned CDN script on the phone page; no build step.

## Data layout

Game content is data, not engine code (GAME-04). Tables live beside the lore as canon:

```
world/
  *.md                 lore (WLD-01 frontmatter)
  data/                game tables, YAML, validated by Pydantic schemas
    affinities.yaml    20 affinities, gods' pairs
    peoples.yaml       5 peoples
    classes.yaml       8 base classes, Tier 1 skill offers, Level 10 evolutions
    skills.yaml        skills: affinity, rarity, cost, cooldown, effect kind
    oaths.yaml         7 Oaths: affinity, perk, Burden
    professions.yaml   15 professions; recipes for the first-version ones
    titles.yaml        titles: condition, bonus, witness needed
    rewards.yaml       XP, Standing, damage and loot tables by tier (G-08)
    flags.yaml         flag registry: kind, who sets it, accept rule (D-024)
    rifts/sunken_stair.yaml
  sealed/              sealed lore and sealed/data/ tables (WLD-04)
  secret/              secret lore
```

The prose in `world/power_tiers.md` stays the readable rulebook; `world/data/` holds the numbers the engine loads. A test checks that the two agree on names (classes, affinities, Oaths, professions).

## Package layout

```
src/pantheon/
  engine/     dice.py, checks.py, character.py, progression.py, skills.py, shards.py,
              combat.py, oaths.py, standing.py, calendar.py, clocks.py, events.py,
              state.py (fold), timeline.py (log, snapshot, fork), tools.py (tool schemas
              and validation), commands.py (player commands), rewards.py
  world/      loader.py, schemas.py, gates.py (reveal-gate grammar)
  sealed/     sealed rules, loaded through the same registry (WLD-04)
  llm/        client.py (LLMClient protocol), mock.py, anthropic_adapter.py
  narrator/   assemble.py, loop.py, validators.py, fallback.py
  memory/     summaries.py, retrieval.py, budget.py
  storage/    db.py (SQLite, WAL, schema_version, upgraders)
  ui/cli/     app.py
  ui/web/     app.py, templates/
  config.py   config.toml and environment
tests/        mirrors src/; fixtures/ holds recorded MockClient transcripts
```

## M0: Scaffold (1 session)

1. `uv init`, `pyproject.toml` with the package layout (Windows-safe paths and line endings, D-021), ruff, mypy (`--strict` on `engine/`), pytest, pytest-cov.
2. `config.py`: load `config.toml` and environment (OPS-02); fail clearly when a model id is missing only for commands that need one.
3. `world/schemas.py` + `loader.py`: parse every `world/**/*.md` frontmatter except `README.md` (id, type from a closed list, visibility, tags, reveal_gate) and every `world/data/*.yaml` and `world/sealed/data/*.yaml` against Pydantic models (WLD-01, WLD-02, D-024).
4. `world/gates.py`: the restricted reveal-gate grammar (comparison, and, or, not, parentheses, dotted paths, bare truthy paths); no `eval`.
5. `storage/db.py`: SQLite in WAL mode, `meta.schema_version`, the tables in `docs/architecture.md` section 5.
6. CLI: `pantheon new` creates a timeline with a seed and rules version (ENG-10), and draws the opening's two gods from the seed (D-017).
7. Tests: every world file loads; a malformed fixture fails the schema; every reveal gate (secret and sealed) parses and every path in it is a registered flag or a state field (NAR-02); no `README.md` is in the lore index; a sealed-type file outside `world/sealed/`, or the reverse, fails the load (WLD-04); the engine import-boundary test.
8. CI: add the uv, ruff, mypy and pytest steps to the existing `check` job with the `efficient-github-actions` skill (CI-06). A `windows-latest` job runs the tests from "Run workflow" only (D-023).
9. Canon batch 2 (`canon:`): first `world/data/` tables for affinities, peoples, Oaths, professions (names only, from canon). `flags.yaml` already exists (D-024); the loader adopts its format.

**Acceptance:** roadmap M0. **You test:** nothing to play; read the M0 report.

## M1.5: Thin narrator loop (first fun check, D-029)

Built right after M1a, before the rest of M1, so the plan's top risks are tested first. The remaining M1 and M2 items land behind the same tool and event pattern.

- Thin M1c: events, pure fold, snapshot every 10 turns, one atomic turn commit. No forks yet.
- Six narrator tools plus `request_check`: `apply_effect`, `grant_xp`, `adjust_standing`, `set_flag`, `register_hook`, `suggest_actions`. The Dual Offer, class, profession and free points are player commands.
- `llm/` (protocol, `MockClient`, Anthropic adapter), `narrator/` (referee, narrator and scribe steps, validators, fallback; D-031), first-guess reward tables, character creation, CLI play and `start.bat`. The narrator is Claude Haiku 5.5 (D-032).
- Not in the slice: class skills, shards, combat exchanges, Last Breath and death, items, coin changes, the calendar, forks, summaries, and streaming prose.

**Acceptance:** the roadmap M2 acceptance against `MockClient`, plus a saved live transcript. **You test:** run `start.bat`, play the opening and a few scenes, and say whether it is fun.

## M1.6: Writing style (D-033, D-034)

**First build, merged in PR #11:** new narrator prompt and turn instructions (third person, past tense, plain prose, engine numbers allowed), 3 to 4 options tagged with what the character really has, plain Oath terms on the menu, the drawn sheet on swearing and level-up, commands on screen.

**Second build, on `style-pass-2` (D-036):** real odds on options that roll exactly what they show, mid-story Ledger notices with chance and roll, and `inspect`. Titles move to M1b; the moment for high-stakes rolls waits for M2.5.

**You test:** play the opening and a few scenes with `start.bat`, and say whether it reads right and is fun.

## M1: Engine core (4 to 6 sessions)

M1a is done. M1b onward come after the M1.5 fun check. Ordered so each step is testable alone.

**M1a Dice and checks** (ENG-03, ENG-04, ENG-05)
- Seeded RNG per timeline, split into named streams (checks, loot, opening draw, rival, world) so rolls in one system never shift another; stream state serialisable for forks (D-022).
- d100 check: chance formula, outcome bands, 01 to 05 and 96 to 00, tier-gap automatic rules, Overcome Conditions (the parts the engine can verify).
- Tests: table-driven tests at every band edge; tier gaps -4 to +4; one fixed-seed determinism test that compares a hash of the event log (GAME-06).

**M1b Character and progression** (ENG-01, ENG-07). Engine built on `m1b-progression` (D-037). Skills, titles and evolutions wait for M3.5's canon batches, and shards for loot, so most of it cannot appear in play yet.
- Character: people, class, profession, five stats, free points, HP/mana/stamina formulas, affinities, skills (rarity, rank), titles, Injuries, Oaths, age.
- Caps: skill rank by tier and affinity; affinity by `tier + 1`; Unwritten caps (D-013).
- XP curve, level-ups, class skill offers (1 of 3 at levels 1, 3, 5, 7, 9), Level 10 gate, Ascension Trial, evolution choice.
- Shards: absorb, fuse fragments, skill evolution at rank 5.
- Player commands (`allocate_point`, `pick_skill`, `absorb_shard`, `fuse_fragments`, `choose_evolution`).

**M1c Event log, replay, fork, versions** (ENG-06, ENG-08, ENG-10, ENG-11). Merged in PR #15 (D-038). Oath timers and daily Boons wait for canon rules, and training gains for G-27.
- One command funnel: validate, then roll, then mutate, then append. A rejected tool call fails at validate and consumes no randomness (D-022).
- Events store resolved outcomes; state is a pure fold; snapshots every 10 turns.
- Save versions upgrade one step at a time through a migration chain; a save newer than the game is refused, never overwritten (ENG-10, GAME-05).
- Fork copies events, turns, snapshots and summaries up to turn N with the RNG state.
- Calendar (1 Seedtide 1,140 AS start, Blank Days), `advance_time`, clocks (one segment per season, neglect rule), petitions as hooks.
- Tests: `hypothesis` generates action sequences; replay equals live state; bounds hold.

**M1d Combat and death**. Built on `m1d-combat` (D-039). Signature traits and real foe tables wait for M3.5.
- Exchanges, enemy intents as data, skill costs and cooldowns, pool regeneration, overspend and Injury roll (D-009), Downed, Last Breath per hostile exchange, Reckoning escalation (fourth is final).

**M1e Reward tables v0** (ENG-09, G-08)
- `rewards.yaml`: XP per kind scaled by tier to hit D-014 pacing; Standing deltas; damage by outcome and rarity; Tier 1 loot tables. A small simulation script checks that the tables reach Tier 2 in about 8 hours of typical play (estimate inputs recorded in DECISIONS as Assumed).

**M1f Dev CLI**
- `pantheon roll`, `pantheon sheet`, `pantheon log`, no LLM. `pantheon fork N` came early, with M1c.

**Acceptance:** roadmap M1; engine coverage at least 90 %. **You test:** read a transcript of a level-up, a shard absorption and an evolution; optional: run the CLI.

## M2: Narrator loop (3 to 4 sessions)

1. `llm/`: `LLMClient` protocol, `MockClient` replaying recorded transcripts, Anthropic adapter with timeouts, backoff and jitter (OPS-01, OPS-03), prompt caching on layers 1 and 2 (OPS-04), per-turn token logging (MEM-04). Provider switch (D-020): the same adapter talks to a local Ollama server through its Anthropic-compatible API (`base_url` in `config.toml`); Ollama lacks prompt caching, `count_tokens` and `tool_choice`, so the budgeter estimates tokens itself and the loop never forces a tool. Ollama's context is set on the server, not per request (D-027); the adapter raises an error when Ollama reports far fewer input tokens than the budgeter sent, so a truncated prompt never narrates.
2. `engine/tools.py`: every tool in `docs/architecture.md` section 6 as a Pydantic schema with engine validation; unknown tools rejected (ENG-02).
3. `narrator/assemble.py`: layers 1 to 3 and 8 in fixed order; recent turns as messages (NAR-01). Layer 3 is a curated view of state (no raw roll logs, no off-scene NPCs, nothing gated), not a full dump (D-022).
4. `narrator/loop.py`: the turn loop in architecture section 3: per-call retry cap, forced-prose round, fallback turn, short commit transaction (NAR-06, NAR-07, OPS-03).
5. `narrator/validators.py`: prose number check with known-name allowlist (NAR-04), plus a list of banned mechanical terms (dice notation, stat abbreviations, "rolled", "chance"); `suggest_actions` rules (NAR-03). The fallback path never raises (NAR-07).
6. Character creation from `world/protagonist_seed.md` and `world/peoples.md`; the opening scene with the two drawn gods (D-017); the rival set up from the refused Oath (D-013).
7. Tallyhouse bounty board as data (hooks and beats) with witnessed Standing and rumours.
8. CLI play with streaming prose and a status panel rendered from state.
9. Before any live-model playtest: an estimate of its cost from your configured model's prices, for your approval (SAFE-04). Ollama runs cost nothing per turn.
10. Side-by-side check: the same 10-turn scripted scenario on Claude and on your chosen Ollama model, scored for tool-call compliance and the NAR-03 and NAR-04 validators, so the default narrator is picked on evidence (D-020).

**Acceptance:** roadmap M2 (10-turn scripted playtest against `MockClient`; rejections retried at most twice; no unsupplied numbers; outage gives a fallback turn). **You test:** play the opening in the terminal, or wait for M2.5.

## M2.5: Phone page (1 session)

- FastAPI app on the owner's Windows PC (D-021): one page with the prose stream (SSE), a text box, suggested-action buttons, and the status panel (HTMX partial) rendered from state. No accounts; reachable on home Wi-Fi and through Tailscale only.
- `start.bat` one-click launcher (starts Ollama with `OLLAMA_CONTEXT_LENGTH=32768` if configured (D-027), then the game) and a short setup guide: install uv, Ollama and Tailscale, allow the port in Windows Firewall.

**Acceptance:** roadmap M2.5. **You test:** play the opening on your phone, at home and once over Tailscale.

## M3: Memory (2 to 3 sessions)

- Scene and chapter summaries stored, never regenerated (MEM-02); FTS5 retrieval keyed on tags, names and location (MEM-03); token budget and trimming order (MEM-04); reveal-gate evaluation and `secret_released` events (NAR-02); a test that no unreleased secret or sealed string appears in any assembled prompt.

**Acceptance:** roadmap M3 (60-turn run within budget; turn-3 fact recalled at turn 55). **You test:** one long session on your phone.

## M3.5: First content pass (2 to 3 sessions, plus canon review rounds)

Canon batches for your approval (`canon:`), each a small PR:

1. Tier 1 skill lists for the 8 base classes (about 8 to 10 skills each) and their Level 10 evolution options (2 to 4 each).
2. Profession skills and recipes for the first-version professions; the Tier 1 shard and item catalogue.
3. The Sunken Stair rift: floors 1 to 6, tier by depth, affinity, foes and intents, loot tables, core.
4. Cinder Ford NPCs, the rival, bounty templates, god petition templates.
5. The Unwritten path's first steps.
6. Sealed: the trace beat and its data (reviewer agent, not you). No player command takes the sealed affinity in the first version (D-012); the engine lock is a missing command, not the reveal gate, and a data test checks that no first-version loot table or shard source grants it.

Then the engine wiring and a full playtest from a new timeline to Tier 2.

**Acceptance:** roadmap M3.5. **You test:** play to Tier 2 (about 8 hours); your notes go into `docs/playtests/` and decide what "fun" means here (GAME-06).

## Total and order

M0 1 session, M1 4 to 6, M2 3 to 4, M2.5 1, M3 2 to 3, M3.5 2 to 3: about 13 to 18 sessions of agent work to the first playable version (estimate), plus your canon reviews and playtests.

## Risks

- **Balance:** the reward tables are guesses until M3.5 playtests. Mitigation: tables are data, and the M1e simulation checks pacing before any play.
- **Narrator obedience:** the model may describe effects it never requested through tools. Mitigation: NAR-04 validator, tool-only state changes, the eval suite in M6.
- **Content volume:** about 70 to 80 skills and 20 or more evolution options for Tier 1 alone (estimate). Mitigation: Claude drafts in batches; you approve each batch.
- **Sealed content drift:** nobody human reads it. Mitigation: reviewer agent on every change; reachability tests (WLD-04).
- **Model cost:** live playtests cost money per turn. Mitigation: MockClient for all automated tests; estimates before any live run.
