---
id: power_tiers
type: rules
visibility: public
tags: [tiers, levels, stats, checks, oaths, callings, ascension, rules]
---

# Power Tiers and Rules

All numbers are initial balance values. The engine is the source of truth; tune them under test.

## Stats

Five stats: **Vigor**, **Agility**, **Intellect**, **Resolve**, **Presence**. Starting range 8 to 16. Modifier = `floor((stat - 10) / 2)`.

## Levels and tiers

Levels run 1 to 70. A tier spans 10 levels. `tier = ceil(level / 10)`. Level 0 is Tier 0 (Unwritten).

- `xp_to_next(level) = round(100 * level ** 1.5)`
- At a level that is a multiple of 10, XP may fill, but advancement to the next level requires an **Ascension Trial**.
- `MaxHP = 10 + (5 + Vigor_modifier) * level`
- Skill rank (0 to 5) is capped by tier: Tier 1 caps at 2, Tier 2 at 3, Tier 3 at 4, Tier 4 and above at 5.

## The ladder

Population basis: 38,000,000. Counts are approximate world totals.

| Tier | Name | Levels | Approx. count | Capability | Typical lifespan |
|---|---|---|---|---|---|
| 0 | Unwritten | 0 | remainder (about 37,003,000) | No Ledger. Ordinary mortals. | 55 years |
| 1 | Inscribed | 1 to 10 | 900,000 | First Oath and Calling. Fights 3 to 5 Unwritten. Heals roughly 2x faster. | 70 to 90 |
| 2 | Bound | 11 to 20 | 85,000 | Second Oath. Skills crystallize into named **Arts**. Equal to a squad of Unwritten soldiers. | 100 to 120 |
| 3 | Vaunted | 21 to 30 | 11,000 | Regional renown. Oaths witnessed by lesser spirits. Gains a **Mantle** (aura affecting allies). Can hold a gatehouse against a Tier 1 host. | 150 to 200 |
| 4 | Hallowed | 31 to 40 | 900 | Saints and champions. One **Miracle** per day. Survives a siege. | about 300 |
| 5 | Exalted | 41 to 50 | 70 | Nation-scale. Bends a local law of nature (a **Verse**). | about 600 |
| 6 | Sovereign | 51 to 60 | 9 | Rules a **Domain**. Co-signs pacts with a god. | Unbounded while the Domain stands |
| 7 | Heir | 61 to 70 | 3 | May hold a divine Seat provisionally. Speaks in the council of Hands. | Unbounded |
| 8 | Hand | n/a | 7 (the gods) | Cannot act directly in the mortal realm (the Vessel clause). | n/a |

## Check resolution

```
total = d20 + stat_modifier + skill_rank + 3 * tier_delta
tier_delta = actor_tier - challenge_tier
```

Base DC by difficulty: **Routine 10, Hard 15, Severe 20, Heroic 25**.

| Total vs DC | Outcome |
|---|---|
| Total >= DC + 10 | Triumph |
| DC <= total < DC + 10 | Success |
| DC - 5 <= total < DC | Success at cost |
| Total < DC - 5 | Failure |

Natural 20 upgrades the outcome one step. Natural 1 adds a complication to any outcome.

**Tier gap rules:**

- `tier_delta >= 3`: the action succeeds without a roll.
- `tier_delta <= -3` on a direct-force action: automatic failure, unless an **Overcome Condition** is met.

**Overcome Conditions** (any one lifts the automatic failure; the roll proceeds with `tier_delta` capped at -2):
**Oath** (an Oath whose Boon applies), **Artifact** (a relic of tier equal to or above the challenge), **Terrain** (a prepared battlefield or Delve feature), **Ally** (a character of sufficient tier committed to the action), **Divine Favor** (Standing 60 or higher with a god whose domain applies).

## Callings

A Calling is chosen at the first Oath. It sets primary stat and starting skill picks.

| Calling | Primary stat | Role |
|---|---|---|
| Blade-sworn | Vigor | Frontline fighter |
| Warden | Resolve | Defender, protector |
| Cantor | Presence | Voice-magic, binding speech |
| Wayfinder | Agility | Scout, tracker, traveler |
| Hearthwright | Intellect | Crafter, healer, alchemist |
| Wager-bound | Agility | Gambler, trickster, luck-worker |
| Gravewalker | Resolve | Ancestor-speaker, ritualist |
| Wildkin | Vigor | Beast-bonded hunter |

## Oaths

An Oath binds a mortal to a god. Each Oath has a **Boon**, a **Burden**, and a **Breach** penalty. A character gains one Oath at Tier 1, a second at Tier 2, and a maximum of one additional Oath per two tiers after that.

| Oath | God | Boon | Burden | Breach |
|---|---|---|---|---|
| Open Hand | Veshra | Sense knowing falsehood in spoken words | Shall not knowingly lie or break a sworn word | Lose all Boon until atoned; Standing -30; a Scar |
| Held Line | Kaul | +2 to checks defending others; resist fear | Shall not abandon a charge or yield a held position unordered | Standing -30; a Scar; lose Boon for a season |
| Turning Tide | Ysmere | Heal-over-time; weather sense | Shall not remain in one place longer than 30 days | Boon lost; storms follow the bearer 7 days |
| Last Rest | Maru-Ghen | Speak to the recently dead; resist decay | Shall not raise or bind the dead; shall see the dying properly buried | Standing -40; ancestors refuse to speak |
| Kept Light | Ilvane | One prophetic glimpse per level-up; see in darkness | Shall not conceal a danger one has foreseen | Prophecy turns false for 30 days |
| Fair Wager | Drovash | Reroll one failed check per day | Shall honor any wager accepted; shall not cheat the unaware | Luck inverts: next three rolls take the lower of two dice |
| Long Hunt | Hurrow | Track any quarry; +2 to Wilds checks | Shall not hunt for sport; shall not enclose the wild | Beasts turn hostile for a season |

**Oath conflict:** two Oaths conflict when their Burdens cannot both be satisfied in a pending situation. The engine detects conflicts. A conflict forces a decision: choose which Oath to honor, seek a Trial of Reconciliation, or accept a Breach.

## Standing

Standing is a value from -100 to +100, tracked per god and per faction.

| Range | Meaning |
|---|---|
| -100 to -60 | Enemy of |
| -59 to -20 | Disfavored |
| -19 to 19 | Neutral |
| 20 to 59 | Favored |
| 60 to 100 | Beloved (Divine Favor available for gods) |

## Ascension Trials

Advancing from level 10, 20, 30, ... requires a Trial. A Trial has four components:

1. **Witness**: a god, a Sovereign, or the world itself (Delve) watches.
2. **Test**: a challenge tied to the character's Oaths, history, or flaws. Never a pure damage race.
3. **Tithe**: a cost. One of: years of life (10 x new tier), a memory (the narrator names it), a relationship (Standing -30 with one entity), or a Name (a formal title, lost).
4. **Outcome**: Ascend, Setback (drop one level and gain a Scar), or Breaking (a permanent Scar, no level change, Trial may not be retried for one in-world year).

A **Scar** is a persistent condition with a narrative and a mechanical effect (-2 to one stat in specific circumstances, or a recurring complication).

## Death

When HP reaches 0 the character is **Downed**. Each hostile round adds one **Last Breath** mark; three marks is death. With `permadeath = false` (default), death offers a **Reckoning**: return at the last Shrine with a Scar and a Tithe, and the world advances 30 days. With `permadeath = true`, death ends the timeline; the player may fork from an earlier turn.
