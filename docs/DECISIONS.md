# Decisions

Settled rules for this project. Not a changelog: an entry stays while the rule is in force. Change a rule here in the same change that changes the behaviour. Mark ideas Proposed until the owner approves them; mark retired entries SUPERSEDED with a pointer, never delete them. Agent assumptions made while building the approved spec use Status "Assumed" (see AGENTS.md).

The requirements themselves live in `docs/SPEC.md` section 2 and the technology choices in its section 3; this file does not copy them.

## D-001 Adopt AI-Master-Instructions (core + game)

- **Status:** Accepted (2026-10-30)
- **Decision:** Pin AI-Master-Instructions v0.5.0 with layers `core` and `project-types/game` in `.ai-master.json`. No stack layer: the master has none for Python. No overrides.
- **Why:** owner asked to integrate the master. `game` covers seeded determinism, one rules engine and AI text never deciding outcomes, which match SPEC ENG-01 to ENG-03. `creative-writing` was not added: project types are used one at a time and Pantheon's canon governance is already in SPEC (WLD-01 to WLD-03).

## D-002 The build spec moves from CLAUDE.md to docs/SPEC.md

- **Status:** Accepted (2026-10-30)
- **Decision:** `CLAUDE.md` holds only `@AGENTS.md` and `@.claude/master/RULES.md`. The spec text is unchanged except paths (`docs/decisions.md` became `docs/DECISIONS.md`). AGENTS.md carries the spec rules every session needs and points to SPEC for the rest.
- **Why:** the master's start-up budget is 200 lines and 24 KB for everything CLAUDE.md loads; the 109-line spec plus 95 lines of shared rules exceeded the line budget, and most of the spec is needed only at milestone start (CTX-06).

## D-003 CI is a drift check until M0

- **Status:** Accepted (2026-10-30)
- **Decision:** `ci.yml` runs only `node .claude/master/sync.mjs --check`. M0 adds uv, ruff, mypy and pytest steps to the same job. Only `docs/**` and `README.md` skip CI; `world/**` does not, because the M0 loader validates canon frontmatter.
- **Why:** no Python project exists yet. The master template skips all `**/*.md`, which would skip canon changes and synced rule changes.

## D-004 `hypothesis` generates action sequences, not seed batteries

- **Status:** Assumed (2026-10-30)
- **Decision:** Engine invariant tests (replay equivalence, bounds) use `hypothesis` to generate action sequences. Determinism (ENG-03) is one fixed-seed test.
- **Why:** reconciles `docs/roadmap.md:21` with GAME-06. See audit item 20.

## D-005 The engine sizes XP, Standing and damage; the narrator chooses other rewards

- **Status:** Accepted (2026-10-30)
- **Decision:** The narrator names the kind of an XP, Standing or damage change and the engine sets the number from a rules table. Items, coin, information and favours are the narrator's choice within engine bounds. Recorded as ENG-09.
- **Why:** owner's answer to audit item 1. Keeps "the engine owns the numbers" (GAME-03) where drift hurts progression most, without making every reward a table entry.

## D-006 Audit fixes applied to the design

- **Status:** Accepted (2026-10-30)
- **Decision:** Audit items 2 to 12 and 20 to 22 are applied to `docs/SPEC.md` (ENG-06, ENG-08 to ENG-11, NAR-03, NAR-04, NAR-07, pytest-cov, import test), `docs/architecture.md` sections 3 to 10, `prompts/narrator.md`, `config.example.toml` and `docs/roadmap.md`. Canon gaps (items 13 to 19) are listed in `docs/canon_gaps.md`, not filled.
- **Why:** owner asked for the audit fixes to be made. Item 9 (model unavailable) follows the recommendation, an engine-rendered fallback turn (NAR-07), so GAME-03 needs no override.
