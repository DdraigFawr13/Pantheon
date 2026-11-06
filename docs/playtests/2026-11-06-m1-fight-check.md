# 2026-11-06 M1 fight check (scripted, not a playtest)

An engine check by the build session, not the owner's playtest: `pantheon session` driven by a script on a scratch save (seed 11), with one-line placeholder prose instead of narration. It shows M1d to M1f through the session-play commands: an Elementalist attunes to Storm, a fight with an Ash Hound (standard) and a Rift Rat (minion) runs one exchange per turn from picked options, and the won fight pays foe XP (two levels), searches both bodies for loot, and ends. The script that made it is not kept; the same steps are covered by `tests/test_session.py`.

Findings:
- Exchange 3 rolled a success against the hound's guarded stance, which takes one hit off, so the hound took none. The summary said "takes 0 hit"; it now says "takes no hit".
- One two-foe fight at Level 1 gave 438 XP and two levels (D-047's numbers). LitRPG-fast, as approved; watch it in play.
- The character attuned to Storm without a Storm affinity (its affinities were Tide and Iron). Canon does not say Attuned needs the affinity; noted for the owner.

```text
$ session choose attunement
  Attuned: Storm
Still to choose: profession: herbalist, miner, hunter, fisher, alchemist, smith, leatherworker, tailor, jeweller, enchanter, scribe, cook, physician, tamer, merchant
```

```text
$ session commit
The Ledger opened in Ddraig's head like a door left ajar. Something growled on the landing below.
  A fight begins: Ash Hound, Rift Rat
1 Seedtide 1,140 AS · Ddraig · Tier 1 · Level 1 · XP 0/100 · HP 58/58
Exchange 1
  Ash Hound (Tier 1, 2 hits left) shows a plain strike
  Rift Rat (Tier 1, 1 hit left) shows a plain strike
  1. [VIGOR 57%] Drive the hound back
  2. [RESOLVE 56%] Brace against the wall
  3. [AGILITY 59%] Swat the rat first
  Or type your own.
```

```text
$ session begin --option 1
Engine check: {"check_id": "c1", "stat": "vigor", "stat_value": 24, "skill": null, "skill_rank": 0, "difficulty": "routine", "challenge_tier": 1, "approach": "force", "stakes": "attack in the fight", "tier_gap": 0, "chance": 57, "roll": 91, "outcome": "failure", "complication": false, "automatic": false, "overcome_applied": false}
Engine fight: Ash Hound takes no hit and has 2 left. Blows land for 18 HP, leaving 40. Ash Hound now shows a guarded stance; Rift Rat now shows a guarded stance. Show this at the end of the scene.
```

```text
$ session commit
Ddraig moved.
***Vigor check: 57% chance, rolled 91: failure***
The Ledger tallied what it cost them both.
  -18 HP (blows in the exchange)
1 Seedtide 1,140 AS · Ddraig · Tier 1 · Level 1 · XP 0/100 · HP 40/58
Exchange 2
  Ash Hound (Tier 1, 2 hits left) shows a guarded stance
  Rift Rat (Tier 1, 1 hit left) shows a guarded stance
  1. [VIGOR 57%] Drive the hound back
  2. [RESOLVE 56%] Brace against the wall
  3. [AGILITY 59%] Swat the rat first
  Or type your own.
```

```text
$ session begin --option 1
Engine check: {"check_id": "c2", "stat": "vigor", "stat_value": 24, "skill": null, "skill_rank": 0, "difficulty": "routine", "challenge_tier": 1, "approach": "force", "stakes": "attack in the fight", "tier_gap": 0, "chance": 57, "roll": 70, "outcome": "failure", "complication": false, "automatic": false, "overcome_applied": false}
Engine fight: Ash Hound takes no hit and has 2 left. No blow lands. Ash Hound now shows a guarded stance; Rift Rat now shows a plain strike. Show this at the end of the scene.
```

```text
$ session commit
Ddraig moved.
***Vigor check: 57% chance, rolled 70: failure***
The Ledger tallied what it cost them both.
1 Seedtide 1,140 AS · Ddraig · Tier 1 · Level 1 · XP 0/100 · HP 40/58
Exchange 3
  Ash Hound (Tier 1, 2 hits left) shows a guarded stance
  Rift Rat (Tier 1, 1 hit left) shows a plain strike
  1. [VIGOR 57%] Drive the hound back
  2. [RESOLVE 56%] Brace against the wall
  3. [AGILITY 59%] Swat the rat first
  Or type your own.
```

```text
$ session begin --option 1
Engine check: {"check_id": "c3", "stat": "vigor", "stat_value": 24, "skill": null, "skill_rank": 0, "difficulty": "routine", "challenge_tier": 1, "approach": "force", "stakes": "attack in the fight", "tier_gap": 0, "chance": 57, "roll": 51, "outcome": "success", "complication": false, "automatic": false, "overcome_applied": false}
Engine fight: Ash Hound takes no hit and has 2 left. Blows land for 9 HP, leaving 31. Ash Hound now shows a plain strike; Rift Rat now shows a plain strike. Show this at the end of the scene.
```

```text
$ session commit
Ddraig moved.
***Vigor check: 57% chance, rolled 51: success***
The Ledger tallied what it cost them both.
  -9 HP (blows in the exchange)
1 Seedtide 1,140 AS · Ddraig · Tier 1 · Level 1 · XP 0/100 · HP 31/58
Exchange 4
  Ash Hound (Tier 1, 2 hits left) shows a plain strike
  Rift Rat (Tier 1, 1 hit left) shows a plain strike
  1. [VIGOR 57%] Drive the hound back
  2. [RESOLVE 56%] Brace against the wall
  3. [AGILITY 59%] Swat the rat first
  Or type your own.
```

```text
$ session begin --option 1
Engine check: {"check_id": "c4", "stat": "vigor", "stat_value": 24, "skill": null, "skill_rank": 0, "difficulty": "routine", "challenge_tier": 1, "approach": "force", "stakes": "attack in the fight", "tier_gap": 0, "chance": 57, "roll": 8, "outcome": "triumph", "complication": false, "automatic": false, "overcome_applied": false}
Engine fight: Ash Hound is down. Blows land for 9 HP, leaving 22. Rift Rat now shows a plain strike. Show this at the end of the scene.
```

```text
$ session commit
Ddraig moved.
***Vigor check: 57% chance, rolled 8: triumph***
The Ledger tallied what it cost them both.
  Ash Hound takes 2 hits
  -9 HP (blows in the exchange)
1 Seedtide 1,140 AS · Ddraig · Tier 1 · Level 1 · XP 0/100 · HP 22/58
Exchange 5
  Rift Rat (Tier 1, 1 hit left) shows a plain strike
  1. [RESOLVE 56%] Brace against the wall
  2. [AGILITY 59%] Swat the rat first
  3. Shout for help
  Or type your own.
```

```text
$ session begin --option 2
Engine check: {"check_id": "c5", "stat": "agility", "stat_value": 32, "skill": null, "skill_rank": 0, "difficulty": "routine", "challenge_tier": 1, "approach": "force", "stakes": "attack in the fight", "tier_gap": 0, "chance": 59, "roll": 18, "outcome": "triumph", "complication": false, "automatic": false, "overcome_applied": false}
Engine fight: Rift Rat is down. No blow lands. The fight is over.
```

```text
$ session commit
Ddraig moved.
***Agility check: 59% chance, rolled 18: triumph***
The Ledger tallied what it cost them both.
  Rift Rat takes 1 hit
  +438 XP (brought down Ash Hound, Rift Rat)
  Level 2! intellect +2, vigor +1
  Level 3! intellect +2, vigor +1
  Loot from Ash Hound's remains:
  +2 sp 10 cp (Ash Hound's remains)
  Loot from Rift Rat's remains:
  +9 cp (Rift Rat's remains)
  The fight ends: no foe is left standing
╭───────────────────────────────── The Ledger ─────────────────────────────────╮
│ Ddraig, 22, saltborn                                                         │
│ Class: Elementalist · Profession: hunter                                     │
│ Trait: Attuned (Storm)                                                       │
│ Tier 1 · Level 3 · 1 Seedtide 1,140 AS                                       │
│ HP      ██████░░░░ 46/82                                                     │
│ Mana    ██████████ 63/63                                                     │
│ Stamina ██████████ 79/79                                                     │
│ XP      █░░░░░░░░░ 55/520                                                    │
│ Purse: 15 sp 7 cp                                                            │
│ Vigor 26 · Agility 32 · Intellect 24 · Resolve 18 · Presence 30              │
│ Affinities: tide 1, iron 1                                                   │
│ Skills: streetwise 1                                                         │
│ Oaths: Held Line                                                             │
│ Standing: harbors +5, underlanes +5                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
The player must choose first (`session choose <kind> <id>`):
  point (2 free): vigor, agility, intellect, resolve, presence
1 Seedtide 1,140 AS · Ddraig · Tier 1 · Level 3 · XP 55/520 · HP 46/82
  1. Catch his breath
  2. Climb on
  3. Check the bodies again
  Or type your own.
```

```text
$ pantheon sheet
╭───────────────────────────────── The Ledger ─────────────────────────────────╮
│ Ddraig, 22, saltborn                                                         │
│ Class: Elementalist · Profession: hunter                                     │
│ Trait: Attuned (Storm)                                                       │
│ Tier 1 · Level 3 · 1 Seedtide 1,140 AS                                       │
│ HP      ██████░░░░ 46/82                                                     │
│ Mana    ██████████ 63/63                                                     │
│ Stamina ██████████ 79/79                                                     │
│ XP      █░░░░░░░░░ 55/520                                                    │
│ Purse: 15 sp 7 cp                                                            │
│ Vigor 26 · Agility 32 · Intellect 24 · Resolve 18 · Presence 30              │
│ Affinities: tide 1, iron 1                                                   │
│ Skills: streetwise 1                                                         │
│ Oaths: Held Line                                                             │
│ Standing: harbors +5, underlanes +5                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

