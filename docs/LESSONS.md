# Lessons

One line per mistake. Read the entries for an area before working in it. When a mistake repeats, bump its count; at ×2 it also becomes a rule (in DECISIONS, AGENTS.md, or proposed to AI-Master-Instructions). Mark retired entries SUPERSEDED; never delete them.

Format: `- <area> · <mistake> · <root cause> · <rule> · ×<n> (<YYYY-MM-DD>)`

- tooling · `ruff format` rewrote a Python code block inside `docs/architecture.md` · ruff formats code in Markdown by default · exclude `docs`, `world`, `prompts` and `*.md` from ruff · ×1 (2026-10-30)
- git · `.gitignore` entry `data/` also ignored `world/data/`, hiding new canon tables from `git status` · unanchored ignore patterns match at any depth · anchor root-only ignores with a leading `/` · ×1 (2026-10-30)
- storage · tests left SQLite connections open (9 ResourceWarnings) · no close path · `Database` is a context manager and pytest treats warnings as errors; open handles also lock files on Windows · ×1 (2026-10-30)
