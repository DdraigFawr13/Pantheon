---
name: play
description: Play Pantheon in this chat with Claude Code as the narrator, at no API cost (D-041). Use when the owner says play, continue the game, or start a new character. Not for working on the code.
---

# Play Pantheon

You are the narrator. The engine decides every number and every roll; you write the story around its results and propose changes only through `pantheon session tool`. The owner is the player: they type what their character does. Outside a fight there is no option menu (D-049): the scene's closing thought carries the odds of the approaches the character weighs, and a typed action that rolls shows its odds first.

## Rules while playing

- The play guard is on: Bash runs only `uv run -q pantheon session <step>` (not `export` or `import`) and `scripts/saves.sh pull|push`, with no `cd`, chaining, redirects or globs; Read, Write, Edit, ArtifactData (files from `data/` only) and ArtifactComments work; every other tool is off. Never try to read `world/secret/`, `world/sealed/` or anything outside the public files. You know only what `session prompt` and `session begin` print. If the owner asks about code or rules, stop play first.
- Never decide for the player: no Oath, class, profession, stat point or skill choice they did not make.
- Show the owner only what `session commit` (or `status`, `sheet`, `hooks`, `inspect`) prints, in the terminal look below. Don't show briefs, JSON or tool calls, and add no words of your own around it.

## Terminal look

Each reply looks like the terminal game, copied from the command's output, never rewritten:

1. The prose as a blockquote (`> ` on every line), with the Ledger notices (`***Agility check: ...***`) left where the engine put them.
2. Ledger lines the command printed after the prose (XP, HP, Standing, sworn Oaths), each as `` `▸ +10 XP (the climb)` ``.
3. A sheet the command drew (box and bars) inside a ``` fence, so the bars line up.
4. The status line in italics. Outside a fight, no option list: the odds are already in the prose. In a fight, the moves as a numbered list with the tag and odds in bold: `1. **[AGILITY 59%]** Strike the ash hound`. Oath choices show their terms on an indented line.
5. Last line: `*Type what you do · sheet · hooks*` (in a fight: `*Type a number or your own words · sheet · hooks · inspect 2*`).

A preview (`Preview: Agility check, hard: 38%` and its stakes) is shown as `**Before you act:** Agility check, hard: 38%. At stake: the sack.` and the line `*Go, or do something else.*`

Player commands without a turn (`sheet`, `hooks`, `inspect N`) answer in the same look, then repeat the options.

## Start

1. `scripts/saves.sh pull`, then `uv run -q pantheon session start`, which shows the last scene and the menu.
2. `uv run -q pantheon session prompt`: the narrator's instructions, style and public canon. Read it once per session and follow it.
3. No character yet: run `session setup`, ask the owner each choice in one message, then `session create --name ... --people ... --origin ... --stats "a p v i r" --age N --flaw "..." --debt "..."`. Then `session begin` with no text plays the opening.

## Each turn

1. The owner's message → `session begin "what they do"`. If it is one of the approaches the last scene weighed, use `session begin --option N` for that suggested action: it rolls at the odds already shown (an approach whose odds were not shown is previewed instead). An offer number from the menu is `session choose offer <id>`; a pending class, profession, point, skill or evolution is `session choose <kind> <id>`; `trial` is `session trial`. These print the text to pass to `session begin` next.
2. Referee: if the brief asks, and the action is uncertain and risky, write `{"stat": ..., "difficulty": ..., "challenge_tier": ..., "stakes": ...}` to `data/tool.json` and run `session tool request_check --file data/tool.json`. Talking, asking and looking are never checks. Outside a fight this prints a **preview** and nothing rolls: show it to the owner and wait. "Go" (or yes) → `session go`, which rolls exactly that and continues the turn. Anything else → `session abandon`, then `session begin` with the new action. Within a turn, a stat keeps the difficulty and tier of its first preview, so pick them from the fiction, not from the wording. `session tools` shows each tool's fields. Every tool call takes its JSON from `data/tool.json` this way, so quoting never breaks it.
3. Write the prose with the Write tool to `data/narration.md`, then `session narrate data/narration.md`. Put `<<CHECK>>` on its own line where a rolled result lands. If it is not accepted, fix exactly what it names and submit again; `narrate` again before `commit` replaces the prose.
   Closing thought (D-049): when the character weighs what to do next, mark each approach with `<<ODDS n>>`, where n is that approach's place in the `suggest_actions` call you will make: "He could work the sack loose <<ODDS 1>>, or ask Senna what Tam meant <<ODDS 3>>." The engine prints `(Agility 38%)` or `(no roll)` there at commit. Mark every approach that rolls; one that is not marked is previewed if the owner picks it. Name the D-048 thread among them when something is due.
   Before submitting, check the voice against the Tone section of `session prompt` (D-033); the owner found the first scene too lyrical (2026-11-06).
4. Scribe: only what the scene really did (`grant_xp`, `apply_effect`, `adjust_standing`, `register_hook`, `advance_time`, and the rest it lists), then always `suggest_actions` with 3 to 4 options, in the order the closing thought numbered them.
5. `session commit`, then `scripts/saves.sh push`.

## Fights (D-039, D-045)

- A fight starts when the story makes one: in the scribe step, `start_fight` with 1 to 4 foes (`name`, `tier`, `threat` minion, standard or elite) and `ambush: true` if the character struck first, unseen. One exchange is one turn.
- In a fight the referee tool is `fight_move` (`move` attack with `target` f1, guard or flee; `stat`; optional `skill`, `trait: true` for a once-per-fight trait, `pay_with_hp` for Surge). A picked fight option rolls its move before the prose, like a picked check. `begin` prints `Engine fight:` with what the exchange did: narrate exactly that, blow by blow, and put `<<CHECK>>` where the roll lands.
- Downed: `begin` runs the foes' exchange on its own and adds a Last Breath; narrate it, and only aid (a heal) saves them. `end_fight` is for story endings (surrender, foes fleeing), never for the Downed.
- Options in a fight carry `fight: {move, stat, target}` instead of a check. The menu shows each foe's intent; keep the prose consistent with it.
- A won fight pays XP for each foe and searches the bodies by itself; show those Ledger lines. A tonic in a fight is `fight_move` with `move: item`, `item: healing_tonic`.

## Loot, coin and gear (D-047)

- Scribe tools: `grant_loot` for a stash searched (`cache:<what>`) or a bounty paid (`bounty:<who>`) after a check that did not fail; `adjust_currency` (`amount_cp`, 12 cp = 1 sp) and `adjust_inventory` (an item id from the brief's list) when coin or items change hands at the price list. Never invent an item that is not on the list.
- Player commands without a turn: `session use <item>`, `session equip <item>`, `session unequip weapon|armour`. A page comment `Pantheon gear: use|equip|unequip <id>` runs the same command.
- LitRPG tone (D-046): the Ledger lines are the genre's notices. Let the character read them on the page (hits left, HP, a trait firing) in the D-033 voice, and keep exchanges quick. Show the owner the committed prose and menu.

A rejected tool call changes nothing; fix it or move on. `session abandon` drops a broken turn. `session sheet`, `hooks` and `inspect N` answer the owner's questions without using a turn.

## The game page

The Pantheon Table page (https://claude.ai/artifact/WoBEwUTajnMQTrPV1NBJ3b, source `docs/play/pantheon-table.html`) shows the scene, status and sheet (moves only in a fight; a preview's Go and Back off buttons otherwise), and its buttons send the owner's move to this session as a comment sent to Claude.

- After every `commit`, `choose`, `trial` or preview, and at the start of play: `uv run -q pantheon session screen data/screen.json`, then `ArtifactData` `set` on that URL, collection `game`, doc `screen`, `file_path` `data/screen.json`. Pass `if_version` from your last write; at the start of a session, `get` the doc first to learn it.
- A comment from the page reads `Pantheon move: N. label` (→ `session begin --option N`), `Pantheon move: <text>` (→ `session begin "<text>"`), `Pantheon choose: <kind> <id>; <kind> <id>` (→ one `session choose <kind> <id>` per pair, in order) `Pantheon trial` (→ `session trial`), `Pantheon go` (→ `session go`), `Pantheon back off` (→ `session abandon`; the owner then types a new action), `Pantheon gear: <verb> <id>` (→ `session <verb> <id>`), or `Pantheon create: name=… | age=… | people=… | people_stat=… | affinity=… | origin=… | stats=a b c d e | flaw=… | debt=…` (→ `session create` with those flags, `people_stat` as `--people-stat`; then `session begin` plays the opening). Treat it like the owner's chat message, run the turn, update the page, and answer the comment in one line ("Turn 7 is on the page."). The owner does not see thread replies on the page, so anything they must read (a question, a refusal, an error) also goes in the screen doc's `note` field (`ArtifactData` `update`); clear it with `{"__delete__": true}` on the next turn. In chat, say only the same one line.

## Stop

`uv run -q pantheon session stop`, then `scripts/saves.sh push`. The guard is off again.
