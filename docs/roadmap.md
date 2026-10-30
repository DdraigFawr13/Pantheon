# Roadmap

Each milestone is playable or testable on its own. Do not begin a milestone until the previous one meets its acceptance criteria.

## M0: Scaffold (1 session)

- `uv` project, package layout from `CLAUDE.md` section 4, `ruff`, `mypy`, `pytest` configured.
- World loader parses every file in `world/` and validates frontmatter (WLD-01).
- `uv run pantheon new` creates an empty timeline in SQLite.

**Acceptance:** all world files load; a schema test fails on a deliberately malformed file; CI-equivalent local command passes.

## M1: Engine core (ENG-01 to ENG-08, OPS-05)

- Character model: stats, derived HP, level, tier, skills (rank cap by tier).
- Dice with seeded RNG; `request_check` resolution per `world/power_tiers.md`.
- Event log, snapshots, replay, fork.
- XP curve and Ascension gating.
- CLI commands to roll checks and inspect state, without any LLM.

**Acceptance:** replay equivalence holds under `hypothesis`; seeded determinism test passes; tier-delta rules covered at deltas -4 to +4; engine coverage at least 90 %.

## M2: Narrator loop (NAR-01 to NAR-06, OPS-01 to OPS-04)

- `LLMClient` protocol, Anthropic adapter, `MockClient`.
- Prompt assembly with layers 1 to 3 and 8; tool-call loop with validation and retry cap.
- Character creation flow from `world/protagonist_seed.md`.
- Streaming output in the CLI; status panel rendered from state.

**Acceptance:** a 10-turn scripted playtest completes with no engine invariant violations; rejected tool calls are surfaced and retried at most twice; no unsupplied numeric outcomes in prose across the scripted run.

## M3: Memory (MEM-01 to MEM-04)

- Scene and chapter summarization with stored results.
- FTS5 retrieval for lore and NPC dossiers.
- Token budgeting and trimming order: recent turns, then retrieved lore, then scene summaries.
- Reveal-gate evaluator and secret-release events (NAR-02).

**Acceptance:** a 60-turn playtest keeps input context at or below the configured budget; the test that scans assembled prompts for unreleased secret strings passes; the narrator recalls a fact introduced in turn 3 at turn 55.

## M4: Branching structure

- Arc skeleton format (beats with preconditions) and beat scheduler.
- Global clocks and a faction tick (clocks advance on elapsed in-world time and on events).
- Hook ledger surfaces due hooks to the narrator.
- Oath conflict detection producing forced-choice scenes.
- Timeline fork command in the CLI.

**Acceptance:** two forks from the same turn with different choices diverge in clock state and available beats; an unresolved hook from turn 5 produces a due-hook entry by its condition; an oath conflict generates a Trial or Breach decision.

## M5: Web UI

- FastAPI app, server-sent event streaming, HTMX status panel, Ledger view (character sheet), Journal view (chronicle), timeline picker with fork.

**Acceptance:** playable on a phone browser on the local network; a session resumes after a server restart at the exact turn.

## M6: Polish and export

- Eval harness (section 9 of the architecture doc) with a saved scenario suite.
- Export a timeline's chronicle to a Markdown "novelization".
- Content settings in `config.toml` (violence level, permadeath on or off).

**Acceptance:** the eval suite runs from one command and reports pass or fail per rule; export of a 60-turn timeline produces a readable chapterized document.

## Deferred (not scheduled)

Embedding retrieval, image generation, multi-character parties, multiplayer, voice.
