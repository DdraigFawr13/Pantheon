---
id: sealed_a
type: sealed-lore
visibility: secret
tags: [sealed]
reveal_gate: "flags.sealed_a_trace_seen and (tier >= 2 or flags.unwritten_path)"
---

# Margin (sealed rare affinity)

Never name this affinity in prose, summaries or hints until this entry's gate opens. Before then the Ledger shows the fifth rare affinity as an unreadable smudge, and the narrator may only describe the trace in `trace_a.md`.

## What it is

Oath magic writes: every blessing, skill and title is a line in the Ledger. **Margin** works in the blank space around the writing. It withholds from the record instead of adding to it. Practitioners call it "keeping the margin". It is older than the Severance and has no god. The Ledger lists Margin skills only as blank lines: it records that they exist, never their content or their use.

## Who can use it

Anyone who absorbs a Margin affinity shard. These shards come only from practitioners (no loot table may contain them; a data test enforces it) and only after this entry's gate opens. No god grants Margin and no Oath raises it. The Unwritten can use it like anyone else, under their normal affinity cap of 3.

## Cost: Erasure

Margin skills spend no mana or stamina, and nothing paid in time. Each use **blanks one of the user's own lines** until the user's next rest:

- **Eligible lines:** a non-Margin skill, a title, or an Oath blessing, of rarity equal to or higher than the Margin skill used (blessings count as Uncommon; titles count as Common). The Unwritten may instead blank a gear property of equal or higher rarity.
- **Not eligible:** Margin skills; a title that unlocks an evolution while a Trial is pending; a line already blank. Each line can be blank once at a time.
- **Effect of a blank line:** it cannot be used and gives no bonus. A blanked blessing loses its perk and its +1 affinity rank until rest; its Burden still binds.
- If no line is eligible, the skill cannot be used.
- During the five Blank Days, Margin skills blank nothing; the Standing cost below still applies.

Gods dislike it: each use while sworn lowers Standing with every god the user is sworn to by 1, at most 3 per god between rests.

## Skills (initial list)

| Skill | Rarity | Effect |
|---|---|---|
| Unrecorded | Common | One deed done this exchange cannot be witnessed through the Ledger or a Tallyhouse record (living witnesses still see it). It does not hide Breaches, XP or Standing; the engine records those as usual |
| Blank Sight | Common | Until next rest, Tallyhouse certification and any skill that reports a tier or rank to its user show the user as Unwritten. Checks still use the user's true tier |
| Refusal | Uncommon | Resist one effect from a blessing or a divine source: the roll proceeds with tier gap raised to -2, even against a god's Vessel |
| Strike-Through | Uncommon | Suppress one named skill of a target for 2 exchanges; the target resists with a Hard Resolve check using the normal tier gap |
| White Space | Rare | For one exchange, no skill or blessing from a source at most one tier above the user can target the user, and the user can use none. Plain weapons and martial attacks without skills still land |

At the same tier, Margin is never simply stronger than Oath magic: it removes options, its own and others', and adds none.

## Story limits

- It touches one secret thread only: the Unwritten's hidden authority (`world/secret/the_seat.md`). Practitioners suspect the Unwritten matter; they do not know about the Pact.
- It has no bearing on any ending.
- Teachers are Unwritten hedge-folk in the Ford Reaches and the Barrow-Lands. The Ashen Convent's purists call it theft from the record; the Tallyhouse would ban it if it knew.

## Engine flags

- `flags.unwritten_path`: set by the engine when the opening resolves with no Oath sworn.
- `flags.sealed_a_trace_ready`: set by the engine on the first `bounty_completed` event in the Ford Reaches.
- `flags.sealed_a_trace_seen`: set by the trace beat itself when it fires (`record_beat`), not by narrator prose. The beat stays due until it fires.
