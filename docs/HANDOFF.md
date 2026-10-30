# Handoff

Updated: 2026-10-30. A fresh session must be able to continue from this file alone. Keep it to 60 lines; move finished entries to `docs/archive/handoff-YYYY-MM.md`.

## Phase

M0 (scaffold) done on branch `ccr-7b10b8f3-92eyt1`, PR pending. Next: M1 (engine core) per `docs/BUILD_PLAN.md`.

## Just done

- 2026-10-30 Integrated AI-Master-Instructions; audit and fixes merged (PR #1).
- 2026-10-30 Design rounds finished and approved (D-007 to D-016).
- 2026-10-30 PR #2 merged. Canon batch: `world/power_tiers.md` rewritten as the d100 System; peoples, economy and calendar drafted; Delves renamed rifts; sealed affinity added under `world/sealed/` and checked by a reviewer agent; random opening gods (D-017); SPEC (ENG-04/05/07, WLD-04), architecture tools, narrator prompt and roadmap (M2.5, M3.5) updated.

- 2026-10-30 M0: uv project, package layout, world loader and reveal-gate grammar, names-only data tables, SQLite store, `pantheon new` with the seeded opening-god draw; 51 tests, engine coverage 100 %, CI runs ruff, mypy and pytest.

## Next

1. Merge the M0 PR, then start M1a (d100 checks) on a fresh branch from `main`.
2. Owner's PC: AMD Radeon RX 6700 XT, 12 GB (2026-10-30). Not on Ollama's Windows ROCm list; Vulkan may work. Before the M2 model test the owner runs `ollama run qwen3:8b` then `ollama ps`; 100 % GPU means local models are viable.

## Open questions

- Does Ollama use the RX 6700 XT through Vulkan? Owner checks with `ollama ps` (cloud sessions cannot reach a Windows machine).
- Reward, loot and evolution numbers are engine data to tune in M1 (canon gap G-08).

## Plan page (D-018)

- https://claude.ai/artifact/HkerL2UNT7oeQcFPW2dZmy: republish whenever the plan or roadmap changes.

## Design forms (owner's answers live in each page's database)

- Round 1: https://claude.ai/artifact/JSEqjnAXHhNCrWkR4fXdwQ
- Review and round 2: https://claude.ai/artifact/RcPLtGKcnpqMVpqvQLtUtQ
- Superseded final check: https://claude.ai/artifact/YQjWtqPffUopaDLGUJ7Ysg
- Round 3 (the System): https://claude.ai/artifact/BwmhqfG5VXYAoR2hd4QwfC
- Final plan (approved): https://claude.ai/artifact/4uyMuu6Xa6dHD2Y9fXQa1s

## Decisions since the last plan update

- 2026-10-30 D-007 to D-023 in `docs/DECISIONS.md` (D-022, D-023 Assumed).
