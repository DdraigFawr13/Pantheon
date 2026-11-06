# Scripted check: odds without an option menu (D-050), 2026-11-06

A scripted session run with seed 42 and the test character Wren (saltborn, Wayfinder). The narrator's prose is placeholder text; every percentage, roll and outcome is the engine's own output, copied from the commands below. The run checks two things: the closing thought gets its odds at commit, and a typed action is previewed before it rolls. This is not the owner's playtest; the owner's next session play is.

Findings:
- The two markers became "(Agility 59%)" and "(no roll)" at commit, and no option menu followed ("Type what you do.").
- The typed climb stopped at "Preview: Agility check, hard: 59%". `session go` then rolled at chance 59, the previewed odds (D-036).
- The briefs, sheet and turn reminders are left out below; everything else is verbatim.

```
$ pantheon session narrate data/narration.md
Prose accepted.
[Scribe step, no more story. Record only what this scene really did; most turns need just one or two calls. grant_xp if a check was passed or survived, if offered. apply_effect if the player was hurt (use a check_id or hazard:<name>). adjust_standing only if a named person or god who matters saw a deed. register_hook only for a new choice or person who should matter later. advance_time whenever the scene took real time, such as a journey or a sleep (rest also heals). send_petition if a sworn god asked a small thing; resolve_petition when one was done or refused. engage_clock if a tested deed touched a global clock's threads. start_fight when foes attack or the player attacks them, and end_fight only if the story ends one early; the engine sets all fight damage, and searches won fights itself. grant_loot when a passed check opened a stash (cache:<what>) or earned a bounty (bounty:<who>). adjust_inventory and adjust_currency when items or coin change hands in the story, at the economy list's prices; invent no item outside the item list. Always finish with suggest_actions: 3 to 4 actions that fit this exact moment, one non-violent, one with a cost or risk in its cost field, no digits. Each label is one brief plain line. Give an uncertain action a check (stat, difficulty, challenge_tier, stakes); talking, asking and looking have none. A line only this character could choose gets a tag naming its Oath, class, profession or people, from the sheet. During a fight, give each action a fight (move, target, stat) instead of a check.]
Tools now: apply_effect, adjust_standing, register_hook, set_flag, advance_time, send_petition, resolve_petition, engage_clock, grant_loot, adjust_inventory, adjust_currency, start_fight, end_fight, suggest_actions. `session tools` shows their fields.
Step: each call's JSON in data/tool.json, then `session tool <name> --file data/tool.json`.

$ pantheon session commit
The Ledger opened in Wren's head. She could climb the broken stair (Agility 59%), or ask the voice what it wanted (no roll).
1 Seedtide 1,140 AS · Wren · Tier 1 · Level 1 · XP 0/100 · HP 58/58
  Type what you do.

$ pantheon session tool request_check {"stat": "agility", "difficulty": "hard", "challenge_tier": 0, "stakes": "a fall"}
Preview: Agility check, hard: 59%
  At stake: a fall. Nothing has been rolled yet.
Step: show the player the preview and wait. `session go` rolls it; `abandon` backs off.

$ pantheon session go
Engine check: {"check_id": "c1", "stat": "agility", "stat_value": 32, "skill": null, "skill_rank": 0, "difficulty": "hard", "challenge_tier": 0, "approach": "other", "stakes": "a fall", "tier_gap": 1, "chance": 59, "roll": 15, "outcome": "triumph", "complication": false, "automatic": false, "overcome_applied": false}
[The engine has decided: a triumph, better than hoped. Narrate exactly that result, and do not soften it. Put <<CHECK>> on its own line at the exact moment the result happens; the game prints the dice there. Write the prose now.]
Step: write the prose to data/narration.md, then `session narrate data/narration.md`.
```
