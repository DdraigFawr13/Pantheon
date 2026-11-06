---
name: chronicle
description: Publish the story so far of the owner's Pantheon character as a phone page, or write it as Markdown for a docs/playtests/ write-up, read straight from the save (D-054). Use when the owner asks to read, recap, publish or share their character's story, or when writing up a playtest. Not while playing (stop play first), and not for working on the code.
---

# The chronicle

`pantheon chronicle` reads a timeline from the save and writes every committed turn in order: the player's words, the accepted prose, the Ledger lines the engine recorded, then the open threads and the sheet. It reports and never decides (GAME-03): every number on the page came from an event.

## Publish the page

1. If `data/pantheon.db` is missing or may be stale, `scripts/saves.sh pull` (it never overwrites a local save, GAME-05).
2. `uv run -q pantheon chronicle --format html --out data/chronicle.html` (add `--timeline <prefix>` for an older timeline; the default is the latest).
3. Publish `data/chronicle.html` with the Artifact tool. The first time, pass `icon` `book` and let the page's own `<title>` name it. Afterwards, pass the chronicle page's URL from `docs/HANDOFF.md` ("Pages") as `url`, so the link stays the same; if HANDOFF has none yet, record the new URL there under "Pages".
4. Reply with one line and the link. The page is private until the owner shares it.

## Write up a playtest

`uv run -q pantheon chronicle --out docs/playtests/<date>-<slug>.md` gives the `## Turns` section in the write-up's shape. Add the header paragraph (narrator, player, timeline, character) and the `## Findings` above it by hand; the findings are the owner's and the narrator's, never the tool's.

## Rules

- Read-only: the command opens the save, writes one file and changes no game state.
- The prose is the narration the engine accepted, so it already passed NAR-04; never edit it in the output.
- Nothing from `world/secret/` or `world/sealed/` is in a save's turns, so nothing on the page can leak it (NAR-02). If a turn ever shows such text, stop and report it instead of publishing.
