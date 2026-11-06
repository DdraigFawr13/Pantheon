# 2026-11-06 M2b scripted run (scripted, not a playtest)

An engine check by the build session, not the owner's playtest (that comes after M2d, D-052). Two 10-turn runs from `tests/test_m2b_scripted_run.py`: `pantheon play` against `MockClient` with scripted player input, and session play as the narrator's command sequence. Placeholder prose, seed 42. Run it again with `uv run pytest -s tests/test_m2b_scripted_run.py`.

What each run covers, by turn: 2 closing-thought odds; 3 a Hard climb previewed, backed off, reworded, previewed again and taken; 4 a tool refused on its try and both retries, then dropped; 5 prose refused once for a stray number; 6 a Routine check rolled at once; 7 three refused narrations, so the engine wrote the turn; 8 a quiet turn (in session play, `suggest_actions` also dropped); 9 a fight starts; 10 a picked fight move.

Checked by the test, on both paths:
- NAR-04: after removing the engine's notices and stamped odds, no saved narration holds a digit, and every notice matches a roll the engine made that turn. The refused "12 coins" never appears.
- NAR-06: `tool_call_dropped` events name exactly the dropped tools (`adjust_standing`, plus `suggest_actions` in session play).
- NAR-07: turn 7 alone is saved with `is_fallback = 1`.
- NAR-08 and D-050: the Hard preview printed twice with the same terms, nothing rolled on the back-off, and turn 2 carries "(Agility 59%)" and "(no roll)".

Findings:
- The fallback text on turn 7 says "Nothing has changed yet. Try again, or try something else." That is right when nothing rolled, as here; with a rolled check it lists the result instead (`narrator/fallback.py`).
- The placeholder scenes cycle, so the hound appears in prose before the fight starts. That is the script's text, not the engine's.

## `pantheon play`

```text
--- Turn 1: [The game begins. Open with The Dual Offer. Narrate the collapse of the Stair as it happens and the fall into the dark. Then each of the two gods speaks to the character directly, with a big personality in its own distinct voice, hinting at its Oath's gift and Burden without spelling them out; the game's menu states the terms. End with both voices waiting for an answer.]
The dark presses close. The first stair groans under you, and the dust has not yet settled.
--- Turn 2: [I swear the open_hand Oath to veshra. The Ledger opens. Narrate the aftermath.]
The rail was wet, and the wind off the ford pulled at her coat. She could climb the rail (Agility 59%), or ask who is there (no roll).
--- Turn 3: I climb the wall, slowly this time
Somewhere below, the ferry chain clanked against its post.
***Agility check: 59% chance, rolled 15: triumph***
--- Turn 4: I ask the guard who keeps this ford
The guard looked at her the way men look at weather.
--- Turn 5: I look around the toll house
Lamplight moved along the wall and found nothing worth keeping.
--- Turn 6: I hop the low rail
The hound came out of the reeds low and fast, already sure of her.
***Agility check: 79% chance, rolled 18: triumph***
--- Turn 7 (fallback): I listen at the door
The narrator falls silent for a moment. The Ledger records only this:
- Nothing has changed yet. Try again, or try something else.
--- Turn 8: I wait for the lamp to pass
Teeth closed on air where her wrist had been a breath before.
--- Turn 9: I draw on the hound
Her boots found the stone, and the stone held.
--- Turn 10: Hold your guard
The river kept its own counsel and its own slow noise.
***Vigor check: 57% chance, rolled 34: success***
```

## Session play

```text
--- Turn 1: [The game begins. Open with The Dual Offer. Narrate the collapse of the Stair as it happens and the fall into the dark. Then each of the two gods speaks to the character directly, with a big personality in its own distinct voice, hinting at its Oath's gift and Burden without spelling them out; the game's menu states the terms. End with both voices waiting for an answer.]
The Stair gave way. Two voices spoke out of the dark at once.
--- Turn 2: [I swear. Narrate the aftermath.]
The Ledger opened in Wren's head. The stair was there to climb (Agility 59%).
--- Turn 3: I climb the slick wall, slowly this time
The rail was wet, and the wind off the ford pulled at her coat.
***Agility check: 59% chance, rolled 15: triumph***
--- Turn 4: I ask the guard who keeps this ford
Somewhere below, the ferry chain clanked against its post.
--- Turn 5: I look around the toll house
The guard looked at her the way men look at weather.
--- Turn 6: I hop the low rail
Lamplight moved along the wall and found nothing worth keeping.
***Agility check: 79% chance, rolled 18: triumph***
--- Turn 7 (fallback): I listen at the door
The narrator falls silent for a moment. The Ledger records only this:
- Nothing has changed yet. Try again, or try something else.
--- Turn 8: I wait for the lamp to pass
The hound came out of the reeds low and fast, already sure of her. She could follow the light.
--- Turn 9: I draw on the hound
Teeth closed on air where her wrist had been a breath before.
--- Turn 10: Hold your guard
Her boots found the stone, and the stone held.
***Vigor check: 57% chance, rolled 34: success***
```
