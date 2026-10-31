# Handoff

Updated: 2026-10-30. A fresh session must be able to continue from this file alone. Keep it to 60 lines; move finished entries to `docs/archive/handoff-YYYY-MM.md`.

## Phase

M1.6 writing style: the first build (D-033 to D-035) is merged in PR #11, with M1a and M1.5 before it (PRs #9, #10). The owner's API key works, and the owner has played one turn of the new style. The second style build has not started.

## Just done

- 2026-10-30 Integrated AI-Master-Instructions; audit and fixes merged (PR #1).
- 2026-10-30 Design rounds finished and approved (D-007 to D-016).
- 2026-10-30 PR #2 merged. Canon batch: `world/power_tiers.md` rewritten as the d100 System; peoples, economy and calendar drafted; Delves renamed rifts; sealed affinity added under `world/sealed/` and checked by a reviewer agent; random opening gods (D-017); SPEC (ENG-04/05/07, WLD-04), architecture tools, narrator prompt and roadmap (M2.5, M3.5) updated.
- 2026-10-30 Owner's GPU check: Ollama 0.40.13 uses Vulkan on the RX 6700 XT; `qwen3:8b` ran at 100 % GPU (37 of 37 layers, 5.6 GB at a 4,096-token context, about 68 tokens/s on one short prompt) with coherent replies. `moondream` gave garbage on a text-only prompt; `qwen3:8b` did not. Local models are viable; narration quality is judged in M2.
- 2026-10-30 Whole-repo audit (`docs/audit/2026-10-30-repo-audit.md`) and its fixes in PR #7: the three M0 blockers (D-024: flag registry in `world/data/flags.yaml` and `world/sealed/data/flags.yaml`, enforced by the loader and `tests/world/test_flags.py`; sealed type and path guard), design fixes (D-025), branch-name practice (D-026), canon corrections and gaps G-10 to G-22. Sealed and secret changes passed the reviewer agent.

- 2026-10-30 M0: uv project, package layout, world loader and reveal-gate grammar, names-only data tables, SQLite store, `pantheon new` with the seeded opening-god draw; 51 tests, engine coverage 100 %, CI runs ruff, mypy and pytest.

- 2026-10-30 M1a: `engine/checks.py` (ENG-04, ENG-05) with band edges, tier gaps -4 to +4, Overcome Conditions and a pinned-hash determinism test (ENG-03). Assumptions in D-028; new gaps G-23, G-24. `.gitattributes` fixes the false drift failure on Windows clones.

- 2026-10-30 M1.5: events and fold, seven narrator tools, Anthropic adapter, referee, narrator and scribe steps (D-031), character creation, CLI play. Four live local-model runs found: the model decided the Dual Offer itself (now a player command), skipped checks (now rolled first), and took 145 to 359 s per turn. The owner rejected local play (D-032).

- 2026-10-30 Style workshop (forms below): third person past, plain prose, engine numbers in prose, tagged options, plain Oath terms, drawn sheet. A blind trial kept Haiku as narrator.

## Next

1. Second style build, recommended but not yet approved by the owner in so many words, on a fresh branch from `main` (`docs/BUILD_PLAN.md` M1.6):
   - Real odds on options, such as `[AGILITY 62%]`. Each suggested action carries its check; the engine works out the chance with the same code that rolls it (GAME-02), and picking it rolls exactly that and skips the referee. A stat or skill tag needs a check. Before the Dual Offer is answered nothing rolls, so strip checks and stat tags then. This fixes the live defect of `[INTELLECT]` on a question that never rolls. Show the chance clamped to 5 to 100 % (`checks.py` `outcome_for`).
   - Mid-story notices: the narrator marks the moment and the engine prints the line; fall back to after the prose if the marker is missing. Don't store the marker in the turn text.
   - `/inspect <number>`, free of game time, using the stored cost field.
   - Proposed to the owner, not confirmed: titles move to M1b because no title data exists; the high-stakes roll moment waits for the phone page. Update BUILD_PLAN and republish the plan page if confirmed (D-018).
2. Then M1b, as the owner chose. Tune `world/data/rewards.yaml` from play.
3. Whenever the owner plays a longer session, save it to `docs/playtests/` from `data/pantheon.db`: this completes M1.5's and M1.6's live transcript. Tables: `turn`, `event` (`payload_json`).

Known from the first live turn (timeline 685eeb5a): about 23,000 tokens in and 4,800 out, about half a cent at list price (estimate from those counts); the prose read well. Watch for invented belongings and injuries (LESSONS).

## Open questions

- Reward, loot and evolution numbers are engine data to tune in M1 (canon gap G-08).
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

- 2026-10-30 D-007 to D-034 in `docs/DECISIONS.md` (D-022, D-023, D-027, D-028, D-030, D-031 Assumed).
