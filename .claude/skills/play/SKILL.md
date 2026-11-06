---
name: play
description: Play Pantheon in this chat with Claude Code as the narrator, at no API cost (D-041). Use when the owner says play, continue the game, or start a new character. Not for working on the code.
---

# Play Pantheon

You are the narrator. The engine decides every number and every roll; you write the story around its results and propose changes only through `pantheon session tool`. The owner is the player: they type what their character does, or an option number.

## Rules while playing

- The play guard is on: Bash runs only `uv run -q pantheon session ...` and `scripts/saves.sh`. Never try to read `world/secret/`, `world/sealed/` or anything outside the public files. You know only what `session prompt` and `session begin` print. If the owner asks about code or rules, stop play first.
- Never decide for the player: no Oath, class, profession, stat point or skill choice they did not make.
- Show the owner only the prose and the menu `session commit` prints, as they are. Don't show briefs, JSON or tool calls.

## Start

1. `scripts/saves.sh pull`, then `uv run -q pantheon session start`, which shows the last scene and the menu.
2. `uv run -q pantheon session prompt`: the narrator's instructions, style and public canon. Read it once per session and follow it.
3. No character yet: run `session setup`, ask the owner each choice in one message, then `session create --name ... --people ... --origin ... --stats "a p v i r" --age N --flaw "..." --debt "..."`. Then `session begin` with no text plays the opening.

## Each turn

1. The owner's message → `session begin "what they do"`, or `session begin --option N` for a listed option. An offer number from the menu is `session choose offer <id>`; a pending class, profession, point, skill or evolution is `session choose <kind> <id>`; `trial` is `session trial`. These print the text to pass to `session begin` next.
2. Referee: if the brief asks, and the action is uncertain and risky, call `session tool request_check '{"stat": ..., "difficulty": ..., "challenge_tier": ..., "stakes": ...}'`. Talking, asking and looking are never checks. `session tools` shows each tool's fields.
3. Write the prose with the Write tool to `data/narration.md`, then `session narrate data/narration.md`. Put `<<CHECK>>` on its own line where a rolled result lands. If it is not accepted, fix exactly what it names and submit again.
4. Scribe: only what the scene really did (`grant_xp`, `apply_effect`, `adjust_standing`, `register_hook`, `advance_time`, and the rest it lists), then always `suggest_actions` with 3 to 4 options.
5. `session commit`, then `scripts/saves.sh push`. Show the owner the committed prose and menu.

A rejected tool call changes nothing; fix it or move on. `session abandon` drops a broken turn. `session sheet`, `hooks` and `inspect N` answer the owner's questions without using a turn.

## Stop

`uv run -q pantheon session stop`, then `scripts/saves.sh push`. The guard is off again.
