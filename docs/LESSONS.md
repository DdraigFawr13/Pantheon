# Lessons

One line per mistake. Read the entries for an area before working in it. When a mistake repeats, bump its count; at ×2 it also becomes a rule (in DECISIONS, AGENTS.md, or proposed to AI-Master-Instructions). Mark retired entries SUPERSEDED; never delete them.

Format: `- <area> · <mistake> · <root cause> · <rule> · ×<n> (<YYYY-MM-DD>)`

- tooling · `ruff format` rewrote a Python code block inside `docs/architecture.md` · ruff formats code in Markdown by default · exclude `docs`, `world`, `prompts` and `*.md` from ruff · ×1 (2026-10-30)
- git · `.gitignore` entry `data/` also ignored `world/data/`, hiding new canon tables from `git status` · unanchored ignore patterns match at any depth · anchor root-only ignores with a leading `/` · ×1 (2026-10-30)
- storage · tests left SQLite connections open (9 ResourceWarnings) · no close path · `Database` is a context manager and pytest treats warnings as errors; open handles also lock files on Windows · ×1 (2026-10-30)
- canon · reveal gates named six flags that nothing set, so three secrets could never release · gates were written before the tool and event lists · every gate path must be a registered flag or a state field, checked by a test (D-024) · ×1 (2026-10-30)
- docs · `docs/canon_gaps.md` cited `path:line` for resolved gaps and the lines moved in the next canon rewrite · line numbers in a ledger go stale · cite file and section in ledgers; keep `path:line` for reports · ×1 (2026-10-30)
- tooling · the drift check failed on every Windows clone though `git status` was clean · Git for Windows sets `core.autocrlf=true` system-wide, which changed synced files' hashes · `.gitattributes` keeps text files LF in every clone · ×1 (2026-10-30)
- audit · the audit told M2 to delete `advance_clock`, but canon allows the narrator to request it · the finding was checked against docs, not canon · check every finding against `world/` as well as DECISIONS before reporting (VER-05) · ×1 (2026-10-30)
