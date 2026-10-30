---
id: power_tiers
type: rules
visibility: public
tags: [system, tiers, levels, stats, checks, classes, affinities, skills, shards, rifts, oaths, professions, titles, rules]
---

# The System

The Ledger is the System: the private status screen every Oathbearer can read in their own mind. All numbers are initial balance values. The engine is the source of truth; tune them under test.

## Checks (d100)

The engine works out a chance and rolls d100. A roll at or under the chance succeeds.

```
chance = difficulty + stat_edge + 5 * skill_rank + 20 * tier_gap
stat_edge = floor((stat - par(actor_tier)) / 5)
par(tier) = 20 + 15 * tier
tier_gap = actor_tier - challenge_tier
```

Difficulty: **Routine 60, Hard 40, Severe 20, Heroic 0.**

| Roll | Outcome |
|---|---|
| Under the chance by 30 or more | Triumph |
| At or under the chance | Success |
| Over the chance by 10 or less | Success at cost |
| Over the chance by more than 10 | Failure |

A roll of 01 to 05 always succeeds and upgrades the outcome one step. A roll of 96 to 00 adds a complication to any outcome.

**Tier gap rules:**

- `tier_gap >= 3`: the action succeeds without a roll.
- `tier_gap <= -3` on a direct-force action: automatic failure, unless an **Overcome Condition** is met.

**Overcome Conditions** (any one lifts the automatic failure; the roll proceeds with `tier_gap` raised to -2): **Oath** (a blessing that applies), **Artifact** (an item of the challenge's tier or higher), **Terrain** (a prepared battlefield or rift feature), **Ally** (a character of sufficient tier committed to the action), **Divine Favor** (Standing 60 or higher with a god whose affinities apply).

## Levels and tiers

Levels run 1 to 70; each tier spans 10 levels: `tier = ceil(level / 10)`. Level 0 is Tier 0 (**Unwritten**). Tier 8 belongs to the gods (the Hands).

- `xp_to_next(level) = round(100 * level ** 1.5)`
- At a level that is a multiple of 10, XP may fill, but the next level requires an **Ascension Trial**, which is also the class **evolution**.
- XP rewards scale with the character's tier so that Tier 1 to Tier 2 takes about 8 hours of play and each later tier about 1.5 times the last.

| Tier | Name | Levels | Approx. count | Stats (typical range) |
|---|---|---|---|---|
| 0 | Unwritten | 0 | about 37,003,000 | 15 to 30 |
| 1 | Inscribed | 1 to 10 | 900,000 | 25 to 45 |
| 2 | Bound | 11 to 20 | 85,000 | 40 to 60 |
| 3 | Vaunted | 21 to 30 | 11,000 | 55 to 75 |
| 4 | Hallowed | 31 to 40 | 900 | 70 to 95 |
| 5 | Exalted | 41 to 50 | 70 | 85 to 110 |
| 6 | Sovereign | 51 to 60 | 9 | 100 to 125 |
| 7 | Heir | 61 to 70 | 3 | 115 to 140 |
| 8 | Hand | n/a | 7 (the gods) | above 140; no ceiling |

Population basis: 38,000,000. Gods cannot act directly in the mortal realm (the Vessel clause); tier gaps make them unbeatable by force.

## Stats and pools

Five stats: **Vigor**, **Agility**, **Intellect**, **Resolve**, **Presence**. Each level the class adds fixed gains to its primary and secondary stats (more at higher tiers), and the character places **1 free point**. Each evolution adds +5 to the new class's primary stat.

- `MaxHP = 2 * Vigor + 10 * level`
- `MaxMana = 2 * Intellect + 5 * level`
- `MaxStamina = 2 * Agility + 5 * level`

Spells cost mana; martial skills cost stamina. Pools refill fully after a rest and by 5 % of their maximum each combat exchange.

**Overspending:** a character may spend up to 50 % of a pool's maximum below zero. Afterwards the engine rolls for a permanent **Injury**: the chance is 2 % for each 1 % of the pool overspent. An Injury is a lasting penalty (-10 to one stat, or -1 rank to one skill) curable only by a Rare or better Life skill or high-grade alchemy.

## Classes

At awakening (the first Oath, which sets Level 1) the character takes a **base class**. A class gives stat gains per level, the skills it offers, and one **signature trait**.

| Base class | Primary / secondary | Signature trait |
|---|---|---|
| Blade-sworn | Vigor / Agility | **Momentum:** each successful exchange in a fight adds +5 to the next attack, up to +15 |
| Warden | Resolve / Vigor | **Bulwark:** may take a blow aimed at an ally within reach |
| Cantor | Presence / Intellect | **Carrying Voice:** Song skills cost 20 % less mana and reach everyone who can hear |
| Wayfinder | Agility / Intellect | **Pathsense:** never lost; acts before enemy intents resolve in the first exchange |
| Hearthwright | Intellect / Resolve | **Kitcraft:** +10 on crafting checks; fuses shards from 2 fragments instead of 3 |
| Wager-bound | Agility / Presence | **Double or Nothing:** before a check, may stake it: success upgrades one step, failure downgrades one step |
| Gravewalker | Resolve / Presence | **Ancestral Voice:** may question the spirits of the dead; Death and Spirit skills cost 20 % less |
| Wildkin | Vigor / Agility | **Bonded Beast:** a beast companion that levels with the character |

**Skill picks:** at levels 1, 3, 5, 7 and 9 of each tier the class offers 3 skills and the player picks 1.

**Evolution:** at level 10, 20, 30 and so on the character passes an Ascension Trial and chooses an evolved class from 2 to 4 options. Options unlock from affinities, skills, titles, Oaths and deeds (for example, Blade-sworn at 10: Emberblade needs Flame 2; Shieldwarden needs the Held Line Oath; Duelist needs Agility 50). Two affinities can unlock a hybrid class. The evolution tree is data.

**Ascension Trial:** a challenge set at the next tier, tied to the character's class, Oaths or history, with a **Witness** (a god, a Sovereign, or the rift itself). Outcomes: **Ascend** (evolve), **Setback** (lose the current level's XP; retry after recovery), **Breaking** (an Injury; retry after recovery).

## Affinities

Twenty magic types: **15 basic** and **5 rare**.

- **Basic:** Flame, Frost, Tide, Storm, Wind, Stone, Iron, Growth, Beast, Light, Shadow, Life, Death, Mind, Song.
- **Rare:** Binding, Space, Blood, Spirit, and one rare affinity the Ledger does not name.

Affinity rank runs 0 to 5. **A skill's rank can never exceed the rank of its affinity.** Affinity rank is capped at `tier + 1`. A character awakens with rank 1 in one or two affinities (from their people and their class). Ranks rise through affinity shards, evolutions, Oath blessings and rare deeds. Sub-affinities (for example Flame into Ash) come later.

## Skills

Every skill has an affinity (or none, for mundane skills), a **rarity** and a **rank**.

- **Rarity** sets the size of the effect: **Common, Uncommon, Rare, Epic, Legendary, Mythic** (Tier 6 and above), **Divine** (Tier 8 only). The same ladder grades items and shards.
- **Rank** (0 to 5) adds 5 per rank to checks. Rank is capped by tier (Tier 1: 2, Tier 2: 3, Tier 3: 4, Tier 4 and above: 5) and by the skill's affinity rank.
- Skills come from class picks, skill shards, and hidden deeds.
- A rank-5 skill plus a matching skill shard can **evolve** to the next rarity.

## Shards and rifts

- A **skill shard** teaches one named skill of its rarity (the character needs rank 1 in its affinity), or upgrades a matching skill.
- An **affinity shard** raises one affinity by 1, up to its cap.
- Three **fragments** of a kind fuse into one shard. Shards can be sold, traded and stolen.

**Rifts** are tears in ground, ruin or open air leading down to sealed, shifting dungeons. Each rift has a tier (sometimes rising with depth) and usually an affinity: a Flame rift drops Flame shards. Clearing floors gives XP, loot and shards. Destroying a rift's **core** closes it permanently and earns a title. Unclosed rifts grow; a rift that breaks open spills monsters into the land (an **Overflow**). Rifters register at a Tallyhouse, and the Ledger records their kills and clears.

## Oaths

An Oath binds a mortal to a god and grants a **blessing**: +1 rank in one of that god's affinities and one **perk**. Each Oath carries one **Burden**. Breaking it is a **Breach**: the blessing is suspended and Standing with the god drops 20 until the character atones (a task the god sets). A character gains one Oath at Tier 1, a second at Tier 2, a third at Tier 4 and a fourth at Tier 6. Any class can swear any Oath; if the class is one the god favours, checks using that god's affinities get +5.

| Oath | God | Affinity | Perk | Burden |
|---|---|---|---|---|
| Open Hand | Veshra | Mind | Sense a knowing falsehood in spoken words | Shall not knowingly lie or break a sworn word |
| Held Line | Kaul | Iron | +10 on checks defending others; resist fear | Shall not abandon a charge or yield a held position unordered |
| Turning Tide | Ysmere | Tide | Recover 5 % HP each exchange; sense coming weather | Shall not remain in one place longer than 30 days |
| Last Rest | Maru-Ghen | Death | Speak to the recently dead | Shall not raise or bind the dead; shall see the dying properly buried |
| Kept Light | Ilvane | Light | One prophetic glimpse per level-up; see in darkness | Shall not conceal a danger one has foreseen |
| Fair Wager | Drovash | Shadow | Reroll one failed check per day | Shall honor any wager accepted; shall not cheat the unaware |
| Long Hunt | Hurrow | Beast | Track any quarry; +10 on Wilds checks | Shall not hunt for sport; shall not enclose the wild |

**Oath conflict:** when two Burdens cannot both be honoured in a situation, the narrator declares it and the player chooses which Oath to honour; the other is breached. Each god will offer two or three Oaths in time; the table holds the first.

## Professions

One profession at awakening, a second at Tier 3. Professions level separately (levels 1 to 70, evolving at 10 and 20 like classes), with their own small skill lists. They never raise tier. Recipes are data; output quality uses the rarity ladder.

- **Gathering:** Herbalist, Miner, Hunter, Fisher.
- **Crafting:** Alchemist, Smith, Leatherworker, Tailor, Jeweller, Enchanter, Scribe (runes), Cook.
- **Service:** Physician, Tamer, Merchant.

## Titles

Earned for firsts and feats: the first clear of a rift, defeating a foe a tier above, a famous deed. Each gives a small bonus (+2 to a stat, or +5 on one kind of check) and some unlock evolution options. Titles and Standing for public deeds need a **witness**: a person present, evidence carried away, or a Tallyhouse record.

## Experience

XP comes from defeating foes (more for foes above the character's tier, very little for those below), clearing rift floors and closing cores, bounties, and story milestones. Profession XP comes from gathering, crafting and trade. The narrator names the kind of reward; the engine sets the amount.

## Standing

Standing is a value from -100 to +100, tracked per god, per faction and per notable person.

| Range | Meaning |
|---|---|
| -100 to -60 | Enemy of |
| -59 to -20 | Disfavored |
| -19 to 19 | Neutral |
| 20 to 59 | Favored |
| 60 to 100 | Beloved (Divine Favor available for gods) |

## Combat

Fights resolve in **exchanges** (usually 1 to 4). Each exchange the narrator shows what each foe intends, the player acts, and the engine rolls. Skills cost mana or stamina and may have cooldowns counted in exchanges.

## The Unwritten

The Unwritten have no class, no level and no blessing. They can still absorb shards: they grow through affinities, skills, gear, allies and reputation. Their skill rank cap is their highest affinity rank (minimum 1), and their affinity cap is 3.

## Death

At 0 HP a character is **Downed**. Each hostile exchange while Downed adds a **Last Breath** mark; three marks is death. With `permadeath = false` (default), death brings a **Reckoning**: the character returns at the last shrine. Each Reckoning costs more:

1. Lose the current level's XP progress.
2. Also lose all carried gear except equipped items.
3. Also lose one level and gain an Injury.
4. The fourth death is final.

With `permadeath = true`, death ends the timeline; the player may fork from an earlier turn.

## Age

Age is recorded on the sheet (starting 16 to 30) and matters in story only. No rule spends it.
