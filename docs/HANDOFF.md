# Handoff

Updated: 2026-10-30. A fresh session must be able to continue from this file alone. Keep it to 60 lines; move finished entries to `docs/archive/handoff-YYYY-MM.md`.

## Phase

Pre-M0. Design docs and canon exist; no code. Milestones: `docs/roadmap.md`. Requirements: `docs/SPEC.md`.

## Just done

- 2026-10-30 Integrated AI-Master-Instructions v0.5.0 (core + game): spec moved to `docs/SPEC.md`, AGENTS.md, CI drift check, settings, PR template (D-001 to D-003).
- 2026-10-30 Audited the design: `docs/audit/2026-10-30-pre-m0.md` (23 findings, all Proposed).

## Next

1. Owner rules on the audit's section A items (engine design), one at a time. Approved items update `docs/architecture.md` and get a DECISIONS entry.
2. Start M0 per `docs/roadmap.md`; seed `docs/canon_gaps.md` with audit section C.

## Open questions

- Audit item 1: should the narrator name reward *kinds* and the engine set the numbers? Recommended: yes.
- Audit item 9: narrator fallback when the model is unavailable, or override GAME-03 for narration? Recommended: a minimal engine-rendered fallback turn.

## Decisions since the last plan update

- 2026-10-30 D-001 to D-004 in `docs/DECISIONS.md`.
