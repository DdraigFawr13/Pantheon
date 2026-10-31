# Lessons

One line per mistake. Read the entries for an area before working in it. When a mistake repeats, bump its count; at ×2 it also becomes a rule (in DECISIONS, AGENTS.md, or proposed to AI-Master-Instructions). Mark retired entries SUPERSEDED; never delete them.

Format: `- <area> · <mistake> · <root cause> · <rule> · ×<n> (<YYYY-MM-DD>)`

- tooling · `ruff format` rewrote a Python code block inside `docs/architecture.md` · ruff formats code in Markdown by default · exclude `docs`, `world`, `prompts` and `*.md` from ruff · ×1 (2026-10-30)
- git · `.gitignore` entry `data/` also ignored `world/data/`, hiding new canon tables from `git status` · unanchored ignore patterns match at any depth · anchor root-only ignores with a leading `/` · ×1 (2026-10-30)
- storage · tests left SQLite connections open (9 ResourceWarnings) · no close path · `Database` is a context manager and pytest treats warnings as errors; open handles also lock files on Windows · ×1 (2026-10-30)
- canon · reveal gates named six flags that nothing set, so three secrets could never release · gates were written before the tool and event lists · every gate path must be a registered flag or a state field, checked by a test (D-024) · ×1 (2026-10-30)
- docs · `docs/canon_gaps.md` cited `path:line` for resolved gaps and the lines moved in the next canon rewrite · line numbers in a ledger go stale · cite file and section in ledgers; keep `path:line` for reports · ×1 (2026-10-30)
- tooling · the drift check failed on every Windows clone though `git status` was clean · Git for Windows sets `core.autocrlf=true` system-wide, which changed synced files' hashes · `.gitattributes` keeps text files LF in every clone · ×1 (2026-10-30)
- narrator · a local model called `resolve_dual_offer` unasked and refused both Oaths for the player · a tool let the narrator make a player's choice, and mock scripts never tried it · choices that belong to the player are player commands, never narrator tools; test against the live model early · ×1 (2026-10-30)
- estimates · I predicted a 1-minute turn twice before measuring and was wrong both times · the cause was guessed from token counts, not read from server timings · read the timing logs first and label a speed claim an estimate until a run confirms it · ×1 (2026-10-30)
- audit · the audit told M2 to delete `advance_clock`, but canon allows the narrator to request it · the finding was checked against docs, not canon · check every finding against `world/` as well as DECISIONS before reporting (VER-05) · ×1 (2026-10-30)
- narrator · I wrote "style" samples from memory of the owner's reference books, and they were moodier than any of the books · I had not read the sources · read a sample of any named reference before imitating or describing it, and try another legitimate source when one refuses · ×1 (2026-10-30)
- estimates · I told the owner a sworn character was Tier 0 with 62 % odds, in the chat test and the blind sample, but an Oath means Tier 1, and that check was 79 % · I worked the sum by hand · get odds from `check_odds` with the real state, never by hand · ×1 (2026-10-30)
- narrator · Haiku's test scene invented belongings and tore the skin after a clean success · the brief did not forbid it · the prompt now forbids both; watch for them in the first real play · ×1 (2026-10-30)
