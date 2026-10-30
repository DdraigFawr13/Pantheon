---
id: protagonist_seed
type: character-creation
visibility: public
tags: [character, creation, origin, opening, hook]
---

# Protagonist Seed

Used by the character-creation flow in M2. The player may override any element with free text; the engine records the result.

## Start state

- Tier 0, Level 0 (Unwritten) until the opening scene grants the first Oath.
- Standard stat array, assigned freely: **14, 13, 12, 10, 9**, plus one stat of the player's choice at +1 from the Origin.
- Starting coin: 12 silver.
- Starting gear: determined by Origin.

## Origins (pick one)

| Origin | Stat bonus | Skill | Starting Standing | Complication |
|---|---|---|---|---|
| **Ledger-clerk's apprentice** | Intellect +1 | Lore 1 | Hale +10, Tallyhouse +5 | Owes a master 40 silver for training |
| **Toll-ferry orphan** | Agility +1 | Streetwise 1 | Harbors +5, Underlanes +5 | A pursuer in the Underlanes remembers your parent |
| **Shrine-sweeper** | Resolve +1 | Ritual 1 | Convent +5, Lantern +5 | Has seen something in the cracked altar they cannot explain |

## Flaw (pick one or write one)

Hot-tempered. Compulsive about debts. Cannot refuse a dare. Distrusts anyone in a uniform. Hoards small objects.

## Debt (pick one or write one)

A sum owed. A favor owed. A name owed. The Debt is registered as a hook at turn 0.

## Opening scene

**Title: The Dual Offer.**

The Sunken Stair collapses under a team of Delvers. The player, working at the edge of the Delve as a porter, a clerk, or a lantern-bearer, is dragged into the fall. In the dark, two voices answer a dying wish. Both are real.

- **Veshra's Weighing Voice** offers the **Open Hand**: the player will always be able to tell when others lie, and must never lie in return.
- **Drovash's Laughing Voice** offers the **Fair Wager**: the player may reroll a failed check each day, and must honor any wager they accept.

The player may accept one, refuse both, or try to bargain. The two gods dislike being asked to share. Accepting one earns the other's quiet interest or open hostility.

**Required engine events from the opening:** `oath_offered` (two), `oath_sworn` (zero or one), `flag_set: opening.dual_offer_resolved`, `hook_registered` (at least two: one for each god's response).

**Narrator guidance:** the scene shall end with the player standing in the rubble of the Stair, a Ledger open in the mind for the first time, an NPC rescuer present (Registrar Hale Dunmore or an Ironmarch caravan-master), and one clear short-term goal. No more than one major reveal in the first 5 turns.
