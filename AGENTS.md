# Agent instructions

Pantheon: a single-player, text-based LitRPG narrated by an LLM over a deterministic Python engine. One owner, local play, 20 to 40 minute sessions.

Shared rules come from AI-Master-Instructions and load through CLAUDE.md (`.claude/master/RULES.md`). This file holds only what is specific to this project. Keep it under 80 lines.

## Read first

1. `docs/HANDOFF.md`: current state and next step.
2. `docs/DECISIONS.md`: settled rules. Don't reopen them.
3. `docs/LESSONS.md`: entries for the area you are about to work in.
4. `docs/SPEC.md`: requirement IDs (section 2) and working agreements (section 5). Then `docs/roadmap.md` and `docs/BUILD_PLAN.md` for the current milestone, and only the `docs/architecture.md` sections it needs.
5. `world/`: open a file only when the task needs its content; the loader and tests need only frontmatter.

## Local checks (run before pushing)

- Every push: `node .claude/master/sync.mjs --check`.
- From M0 on: `uv run ruff check . && uv run mypy src/pantheon/engine && uv run pytest`.

## What CI runs

- **CI** (`ci.yml`): the drift check on every PR update and `main` push; M0 adds the Python checks. Changes only to `docs/**` or `README.md` skip it. `world/` changes do not skip it: the loader validates canon frontmatter.
- **Delete merged PR branches** (`prune-merged-branches.yml`): on PR close.
- No deploys.

## Project rules

- The engine owns every number; the narrator proposes changes through typed tool calls and the engine accepts or rejects them (ENG-01, ENG-02). Narrator prose never states a number the engine did not return that turn (NAR-04).
- `src/pantheon/engine/` never imports `narrator`, `llm` or `ui`; a test enforces it (SPEC section 4).
- `world/` is canon and read-only. Edit it only when asked, with a `canon:` commit prefix (WLD-03). List gaps in `docs/canon_gaps.md`; never fill them silently.
- Text from `world/secret/` and `world/sealed/` never appears in a prompt, log line or fixture except a test of the reveal gate (NAR-02).
- Sealed canon (`world/sealed/`, `src/pantheon/sealed/`) is not shown to the owner: describe it only by file name and outline item; a reviewer agent checks every change (WLD-04).
- No model identifier or API key in source; they come from `config.toml` or the environment (OPS-02).
- Write the failing test first for every ENG requirement and put the requirement ID in the test name and commit message.
- `docs/SPEC.md` and `docs/roadmap.md` are approved scope: build them without asking, and record each assumption in `docs/DECISIONS.md` with Status "Assumed". Anything outside them follows WS-02.
- Dependencies named in SPEC section 3 are approved. Ask before any other (SAFE-03) and record it in DECISIONS.
- After each milestone, report requirements satisfied, deferred and known defects, and save a playtest transcript to `docs/playtests/` if it touched the narrator loop.

## Overrides

Master rules this project deliberately changes. Each line names the rule id and the reason; the same entry is in `.ai-master.json` "overrides".

- None.
