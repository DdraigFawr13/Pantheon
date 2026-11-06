# Roadmap

Each milestone is playable or testable on its own. Do not begin a milestone until the previous one meets its acceptance criteria.

## M0: Scaffold (1 session)

- `uv` project, package layout from `docs/BUILD_PLAN.md`, `ruff`, `mypy`, `pytest` configured.
- World loader parses every lore file in `world/` (not `README.md`) and every `world/data/` table, and validates frontmatter (WLD-01).
- `uv run pantheon new` creates an empty timeline in SQLite.

**Acceptance:** all world files load; every reveal-gate path resolves to a registered flag or a state field (NAR-02); a schema test fails on a deliberately malformed file; CI-equivalent local command passes.

## M1.5: Thin narrator loop (first fun check, D-029)

- After the dice from M1: events and fold, seven narrator tools, the LLM adapter, the turn loop, character creation and CLI play on Claude Haiku 5.5 (D-032). Details: `docs/BUILD_PLAN.md`.

**Acceptance:** a 10-turn scripted playtest against `MockClient` with an outage produces no invariant violations, no lost events and no unsupplied numbers; a live transcript is saved; the owner plays it and reports whether it is fun.

## M1.6 and M1.7: Real odds and session play

- M1.6 (D-036): options show the real odds of their check, and mid-story Ledger notices land where the narrator marks them. Scope in `docs/BUILD_PLAN.md`.
- M1.7 (D-041): play in a Claude Code session, with the session as the narrator, the play guard and saves on the `saves` branch. Scope in `docs/BUILD_PLAN.md`.

## M1: Engine core (ENG-01 to ENG-11, OPS-05)

- Character model per `world/power_tiers.md`: people, class, profession, stats and free points, HP/mana/stamina, affinities, skills (rarity, rank, caps), shards, titles, Injuries.
- Dice with seeded RNG; d100 `request_check` resolution (ENG-04, ENG-05).
- Class offers, evolutions and Ascension Trials as data; shard absorb and fusion; overspend and Injury.
- Event log of resolved outcomes, snapshots, replay, fork (copies turns and summaries); schema and rules versions.
- In-world calendar and `advance_time`; reward and loot tables for XP, Standing, damage and shards, tuned to D-014 pacing.
- Combat exchanges with enemy intents, Downed and Last Breath, Reckonings.
- XP curve and Ascension gating.
- CLI commands to roll checks and inspect state, without any LLM.

**Acceptance:** replay equivalence holds under `hypothesis`; seeded determinism test passes; tier-gap rules covered at gaps -4 to +4; d100 outcome bands covered at their edges; engine coverage at least 90 %.

## M2: Narrator loop (NAR-01 to NAR-08, OPS-01 to OPS-04)

Built in M1.5 to M1.7: the `LLMClient` protocol, the Anthropic adapter, `MockClient`, prompt assembly, the API loop with retry cap and fallback, the validators, character creation and session play. Remaining (D-050 to D-052):

- M2a: odds without a menu (built in PR #25, D-050); only Hard checks or harder stop at the preview (D-051); 150 to 250 word scenes.
- M2b: retry cap, dropped-call log and fallback turn in session play; D-050's design in `pantheon play`.
- M2c: `introduce_npc`, `introduce_location`, `offer_oath`, `test_burden`, `advance_clock`.
- M2d: a first Tallyhouse bounty board and `record_beat`.
- Status panel rendered from state (built); no streaming (D-029).

**Acceptance:** a 10-turn scripted playtest on both play paths completes with no engine invariant violations; rejected tool calls are surfaced and retried at most twice; no unsupplied numeric outcomes in prose; a model outage produces a fallback turn and no lost events; a preview draws no random numbers before confirm; the owner plays a session with a fight and records the findings.

## M2.5: Phone page

- Minimal web page served locally: prose stream, text input, suggested actions, status panel rendered from state (D-015).

**Acceptance:** the opening plays end to end on a phone browser on the local network.

## M3: Memory (MEM-01 to MEM-04)

- Scene and chapter summarization with stored results.
- FTS5 retrieval for lore and NPC dossiers.
- Token budgeting and trimming order: recent turns, then retrieved lore, then scene summaries.
- Reveal-gate evaluator and secret-release events (NAR-02).

**Acceptance:** a 60-turn playtest keeps input context at or below the configured budget; the test that scans assembled prompts for unreleased secret strings passes; the narrator recalls a fact introduced in turn 3 at turn 55.

## M3.5: First content pass (first playable version)

- The Sunken Stair as the first rift (data template: floors, tier, affinity, loot tables, core).
- Tier 1 class skill lists and the Level 10 evolution options for the 25 base classes (D-042); profession recipes for the first-version professions.
- One rival (D-013), Tallyhouse bounty board, the Unwritten path, god petitions, witnessed deeds and rumours.
- The sealed affinity's first trace (WLD-04).

**Acceptance:** a playtest reaches Tier 2 from a new timeline; the sealed reviewer and the reveal-gate reachability test pass; the owner's playtest notes are recorded.

## M4: Branching structure

- Arc skeleton format (beats with preconditions) and beat scheduler.
- Soft guidance back to the story (owner, 2026-11-06; D-048): when the player strays, the scheduler keeps open threads that lead to planned story lines and progression in reach. A due beat or hook gets one way back in each turn's options and closing thought, in the scene's own terms. It is never forced and never labelled "main quest", and if the player ignores it the world moves on. It replaces D-048's prompt rule with an engine-chosen thread.
- Global clocks and a faction tick (clocks advance on elapsed in-world time and on events).
- Hook ledger surfaces due hooks to the narrator.
- Oath conflict detection producing forced-choice scenes.
- Timeline fork command in the CLI.

**Acceptance:** after five turns spent off the planned threads, each turn still offers one way back to the most urgent due beat or hook; two forks from the same turn with different choices diverge in clock state and available beats; an unresolved hook from turn 5 produces a due-hook entry by its condition; an oath conflict generates a Trial or Breach decision.

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
