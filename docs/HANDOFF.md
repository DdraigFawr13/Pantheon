# Handoff

Updated: 2026-11-06. A fresh session must be able to continue from this file alone. Keep it to 60 lines; move finished entries to `docs/archive/handoff-YYYY-MM.md`.

## Phase

M1.7 (D-041), play in Claude Code with the session as narrator, is a draft PR on `ccr-2cd1b9d3-xt21f0`, waiting for the owner's approval. The v4.4.0 upgrade (#17) and M1c (#15) are merged. M1d combat (#16, D-039) is an open draft. The owner's API key works, but only one turn of the new style is saved.

## Just done

- 2026-10-30 PR #2 merged. Canon batch: `world/power_tiers.md` rewritten as the d100 System; peoples, economy and calendar drafted; Delves renamed rifts; sealed affinity added under `world/sealed/` and checked by a reviewer agent; random opening gods (D-017); SPEC (ENG-04/05/07, WLD-04), architecture tools, narrator prompt and roadmap (M2.5, M3.5) updated.
- 2026-10-30 Owner's GPU check: Ollama 0.40.13 uses Vulkan on the RX 6700 XT; `qwen3:8b` ran at 100 % GPU (37 of 37 layers, 5.6 GB at a 4,096-token context, about 68 tokens/s on one short prompt) with coherent replies. `moondream` gave garbage on a text-only prompt; `qwen3:8b` did not. Local models are viable; narration quality is judged in M2.
- 2026-10-30 Whole-repo audit (`docs/audit/2026-10-30-repo-audit.md`) and its fixes in PR #7: the three M0 blockers (D-024: flag registry in `world/data/flags.yaml` and `world/sealed/data/flags.yaml`, enforced by the loader and `tests/world/test_flags.py`; sealed type and path guard), design fixes (D-025), branch-name practice (D-026), canon corrections and gaps G-10 to G-22. Sealed and secret changes passed the reviewer agent.
- 2026-10-30 M0: uv project, package layout, world loader and reveal-gate grammar, names-only data tables, SQLite store, `pantheon new` with the seeded opening-god draw; 51 tests, engine coverage 100 %, CI runs ruff, mypy and pytest.

- 2026-10-30 M1a: `engine/checks.py` (ENG-04, ENG-05) with band edges, tier gaps -4 to +4, Overcome Conditions and a pinned-hash determinism test (ENG-03). Assumptions in D-028; new gaps G-23, G-24. `.gitattributes` fixes the false drift failure on Windows clones.

- 2026-10-30 M1.5: events and fold, seven narrator tools, Anthropic adapter, referee, narrator and scribe steps (D-031), character creation, CLI play. Four live local-model runs found: the model decided the Dual Offer itself (now a player command), skipped checks (now rolled first), and took 145 to 359 s per turn. The owner rejected local play (D-032).

- 2026-10-30 Style workshop (forms below): third person past, plain prose, engine numbers in prose, tagged options, plain Oath terms, drawn sheet. A blind trial kept Haiku as narrator.

- 2026-10-30 M1c: `pantheon fork N` and `play --timeline`, schema 2 with a step-by-step upgrade and a backup, refusal of unreadable saves, calendar and `advance_time`, five clocks with the neglect rule, petitions. Hypothesis checks that replay through a real save equals live state. Tried on a copy of the owner's save: all events and turns kept, original unchanged. Its two old timelines cannot fork before their last recorded dice (D-038).

- 2026-11-06 M1.7 (D-041): `pantheon session` (start, prompt, setup, create, begin, tool, narrate, commit, choose, trial and more), `/play` skill, `play-guard` hook, `scripts/saves.sh` with the `saves` branch. 409 tests pass at 96.79 % coverage. Not yet tried: a push to the `saves` branch from a cloud session.

- 2026-11-03 Master upgrade to v4.4.0 (D-040): sync run twice, `--check` OK, 397 tests pass at 97.65 % coverage, guard hook asks on `git push --force`. CI now skips draft PRs.

## Next

0. Owner approves and merges M1.7. Then the owner says "play" in a Claude Code session: the `/play` skill pulls the save, and each turn pushes it to the `saves` branch. The owner's PC save stays on the PC unless pushed with `scripts/saves.sh push` (Git Bash).
1. Watch in session play: whether the play guard blocks anything play needs, and whether the `saves` push works from the cloud. Same watch list as API play: checks given, `<<CHECK>>` placed, `advance_time` used, no invented belongings or injuries.
2. Next in the plan is M1d (combat, #16), then M1e (rewards and loot). M1d's new tools (`start_fight`, `fight_move`, `end_fight`) need session support when it merges: `fight_move` is rolled before prose like `request_check`. Tune `world/data/rewards.yaml` from play.
3. Whenever the owner plays a longer session, save it to `docs/playtests/` from `data/pantheon.db`: this completes M1.5's and M1.6's live transcript. Tables: `turn`, `event` (`payload_json`).

Known from the first live turn (timeline 685eeb5a): about 23,000 tokens in and 4,800 out, about half a cent at list price (estimate from those counts); the prose read well. Watch for invented belongings and injuries (LESSONS).

## Open questions

- Reward, loot and evolution numbers are engine data to tune in M1 (canon gap G-08).
- What does training give (G-27)? Time skips work; training gains nothing until the owner answers.
- Do the D-038 clock rates hold in play? With every clock neglected, The Lantern's Price fills after 180 counted days.
- Owner confirms the PR #7 canon corrections (sea travel 100 km per day, Tier 0 stat range 15 to 35) and answers gaps G-10 to G-20 before the M3.5 content batches need them (`docs/canon_gaps.md`).

## Plan page (D-018)

- https://claude.ai/artifact/HkerL2UNT7oeQcFPW2dZmy: republish whenever the plan or roadmap changes.

## Design forms (owner's answers live in each page's database)

- Round 1: https://claude.ai/artifact/JSEqjnAXHhNCrWkR4fXdwQ
- Review and round 2: https://claude.ai/artifact/RcPLtGKcnpqMVpqvQLtUtQ
- Superseded final check: https://claude.ai/artifact/YQjWtqPffUopaDLGUJ7Ysg
- Round 3 (the System): https://claude.ai/artifact/BwmhqfG5VXYAoR2hd4QwfC
- Final plan (approved): https://claude.ai/artifact/4uyMuu6Xa6dHD2Y9fXQa1s
- Style round 1: https://claude.ai/artifact/5fnPKcTrTudPap9ozbqjTV
- Style round 2 (approved): https://claude.ai/artifact/3yHuM5FmjjJ7Pee81qzgnc

## Decisions since the last plan update

- 2026-11-06 D-007 to D-038, D-040, D-041 in `docs/DECISIONS.md` (D-022, D-023, D-027, D-028, D-030, D-031, D-037, D-038 Assumed).
