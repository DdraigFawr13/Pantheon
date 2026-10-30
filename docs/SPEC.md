# Pantheon build specification

## 1. Mission

Build a single-player, text-based, AI-narrated LitRPG in a medieval fantasy world (`world/`). The player acts as one character through free-text or suggested actions. The world is persistent, state-driven, and branching. Scope is grand: gods, a tiered power ladder (Tier 0 to Tier 8), factions, global clocks, and long-horizon consequences.

Primary user: one person, local use, short play sessions (20 to 40 minutes). Sessions shall resume exactly where they ended.

## 2. Requirements

Requirement IDs are stable. Reference them in commits and tests.

### 2.1 Engine (ENG)

- **ENG-01** The engine shall be the sole authority for numeric state: stats, HP, XP, level, tier, currency, inventory counts, standing values, and clocks.
- **ENG-02** The narrator shall not write state directly. It shall request changes through typed tool calls. The engine shall validate each call against the rules and return `accepted` or `rejected` with a reason.
- **ENG-03** All randomness shall derive from a seeded RNG stored per timeline. Identical seed and identical inputs shall reproduce identical outcomes.
- **ENG-04** Checks shall resolve as `d20 + stat_modifier + skill_rank + 3 * tier_delta` against a base DC (10, 15, 20, 25), where `tier_delta = actor_tier - challenge_tier`. Natural 20 shall upgrade the outcome one step. Natural 1 shall add a complication. Rules detail: `world/power_tiers.md`.
- **ENG-05** If `tier_delta <= -3` on a direct-force action, the check shall fail automatically unless an Overcome Condition is satisfied (Oath, Artifact, Terrain, Ally, Divine Favor); when satisfied, the roll shall proceed with `tier_delta` capped at -2. If `tier_delta >= 3`, the check shall succeed automatically without a roll.
- **ENG-06** Every state change shall be appended to an immutable event log. Events shall record resolved outcomes (rolls, totals, deltas), not requests, so replay is a pure fold that never re-rolls. Current state shall be derivable by replaying the log from the timeline origin.
- **ENG-07** Tier advancement shall require an Ascension Trial. XP alone shall not advance a tier.
- **ENG-08** Timelines shall be forkable from any prior turn. A fork shall copy the event log, turn records and stored summaries up to that turn, and the RNG state at that turn.
- **ENG-09** The narrator shall choose the kind of an XP, Standing or damage change; the engine shall set its size from a rules table. The narrator may choose other rewards (items, coin, information, favours) within engine-validated bounds.
- **ENG-10** Each timeline shall record the rules version it was created under. Saves shall carry a schema version and upgrade on load; an unreadable save shall never be overwritten.
- **ENG-11** In-world time shall be engine state (a day counter from 1,140 AS), advanced only by events. The engine shall never read the wall clock for game state.

### 2.2 Narrator (NAR)

- **NAR-01** The narrator prompt shall be assembled from layers in a fixed order (section 4 of `docs/architecture.md`) to keep the canon prefix cache-stable.
- **NAR-02** The narrator shall receive secret lore only when the engine evaluates the entry's `reveal_gate` as satisfied. Secret entries not yet released shall not appear in the prompt.
- **NAR-03** Each turn shall offer 3 to 5 suggested actions through the `suggest_actions` tool and shall accept free text. The engine shall reject a set without at least one non-violent suggestion and at least one with a visible cost or risk.
- **NAR-04** Narrator prose shall not contain numeric outcomes (damage, XP, DCs, rolls) except values returned by the engine in the same turn. A runtime validator shall reject prose that breaks this; the rejection counts toward NAR-06. The status panel shall be rendered by the UI from state, not written by the narrator.
- **NAR-05** Every significant choice shall register at least one downstream hook in the consequence ledger (`register_hook`). The engine shall surface due hooks to the narrator as prompt material.
- **NAR-06** On an invalid tool call, the engine shall return the rejection reason to the narrator and permit at most 2 retries before the turn proceeds without the rejected change and logs the failure.
- **NAR-07** If the model is unavailable after retries, the turn shall complete with engine-rendered text (the check result in plain words and the previous suggested actions), marked as a fallback turn.

### 2.3 Memory (MEM)

- **MEM-01** Context shall be built from five layers: canon, character state, chronicle summaries, retrieved lore, recent turns.
- **MEM-02** At each scene boundary the system shall produce a scene summary. At each chapter boundary (default every 10 scenes) it shall produce a chapter summary. Summaries shall be stored, not regenerated.
- **MEM-03** Lore and NPC dossier retrieval shall use SQLite FTS5 keyed on tags, names, and current location. Embeddings are out of scope until a measured retrieval failure justifies them.
- **MEM-04** Input context per turn shall target at most 20,000 tokens, excluding the cached canon prefix. The budget shall be configurable. The system shall log input, cached, and output tokens per turn.

### 2.4 World data (WLD)

- **WLD-01** Lore files shall be Markdown with YAML frontmatter: `id`, `type`, `visibility` (`public` or `secret`), `tags`, and optional `reveal_gate`.
- **WLD-02** Files under `world/` are canon and read-only at runtime. Runtime world changes shall be stored in the timeline's state overlay.
- **WLD-03** Changes to canon files shall be flagged in the commit message with the prefix `canon:`.

### 2.5 Operations (OPS)

- **OPS-01** The LLM client shall sit behind a provider-neutral interface (`LLMClient` protocol). The first adapter targets the Anthropic API. A deterministic `MockClient` shall exist for tests.
- **OPS-02** Model identifiers, API keys, and budgets shall come from environment or `config.toml`. No model identifier shall appear in source code.
- **OPS-03** Network calls shall use timeouts and exponential backoff with jitter. Failures shall not corrupt the event log. A turn is committed atomically or not at all.
- **OPS-04** Prompt caching shall be applied to the canon prefix.
- **OPS-05** Engine code shall have at least 90 % line coverage. Narrator-loop code shall be tested against `MockClient` with recorded tool-call transcripts.

## 3. Technology decisions

| Concern | Decision | Rationale |
|---|---|---|
| Language | Python 3.12+ | Owner familiarity; strong typing via Pydantic |
| Packaging | `uv` | Reproducible, fast |
| Storage | SQLite (WAL mode) | Single file, transactional, FTS5 built in |
| Schemas | Pydantic v2 | Tool-call validation and state models |
| First UI | CLI (`rich`) | Fastest path to a playable loop |
| Second UI | FastAPI + server-sent events + HTMX | Streaming prose, no SPA build step |
| Tests | `pytest`, `pytest-cov`, `hypothesis` for engine invariants | Seeded, deterministic; coverage measures OPS-05 |
| Lint/type | `ruff`, `mypy --strict` on `engine/` | Engine correctness is the project's backbone |

## 4. Layout to create

```
src/pantheon/
  engine/        # rules, dice, tiers, checks, events, state (no LLM imports)
  narrator/      # prompt assembly, tool-call loop, validators
  memory/        # summaries, retrieval, context budgeting
  world/         # loader for world/*.md, reveal-gate evaluator
  llm/           # LLMClient protocol, Anthropic adapter, MockClient
  ui/cli/        # M1 to M3 interface
  ui/web/        # M5 interface
tests/
data/            # saves (git-ignored)
```

The `engine/` package shall not import from `narrator/`, `llm/`, or `ui/`. Enforce with a pytest that walks the imports under `engine/` (no extra dependency).

## 5. Working agreements for Claude Code

1. Read `docs/architecture.md` and `docs/roadmap.md` before the first edit. Work one milestone at a time.
2. State assumptions explicitly in `docs/DECISIONS.md` (date, decision, rationale). Do not stop to ask unless a decision is irreversible.
3. Write the failing test first for every ENG requirement.
4. Do not edit `world/` except under WLD-03. Gaps in canon shall be listed in `docs/canon_gaps.md` and not invented silently.
5. Keep commits small and reference requirement IDs.
6. After each milestone, run the full test suite and report: requirements satisfied, requirements deferred, known defects.
7. Do not add dependencies without recording them in `docs/DECISIONS.md`.

## 6. Definition of done (per milestone)

- All acceptance criteria in `docs/roadmap.md` for the milestone pass.
- `ruff`, `mypy --strict` (engine), and `pytest` pass.
- A short playtest transcript is saved to `docs/playtests/` for any milestone that touches the narrator loop.
- `docs/DECISIONS.md` is current.

## 7. Commands (to be created in M0)

```
uv run pantheon new      # create a timeline
uv run pantheon play     # resume the active timeline
uv run pantheon fork N   # fork from turn N
uv run pytest
uv run ruff check . && uv run mypy src/pantheon/engine
```
