# Canon gaps

Rules or facts the engine needs that `world/` does not settle. Never fill one silently: the owner answers, the answer goes into `world/` in a `canon:` commit (WLD-03), and the line here is marked RESOLVED with the commit.

Format: `- G-<n> · <gap> · <where it shows> · <status>`

- G-01 · Skill rank cap at Tier 0 · `world/power_tiers.md:23` starts at Tier 1, but every Origin grants rank 1 at Tier 0 (`world/protagonist_seed.md:23-25`) · RESOLVED: Tier 0 skill cap 1; the Unwritten's cap is their highest affinity rank (D-013)
- G-02 · How Level 0 becomes Level 1, and what happens if the player refuses both offers · `world/protagonist_seed.md:14`, `:44` · RESOLVED: the first Oath sets Level 1; refusing both keeps the player Unwritten (`world/protagonist_seed.md`)
- G-03 · Oath count above Tier 2 ("one additional Oath per two tiers after that": Tier 4 or Tier 3?) · `world/power_tiers.md:84` · RESOLVED: Oaths at Tiers 1, 2, 4 and 6 (D-010)
- G-04 · What a "hostile round" is for Last Breath marks · `world/power_tiers.md:123` · RESOLVED: a hostile round is a combat exchange (`world/power_tiers.md`, Death)
- G-05 · Character age, needed for the "years of life" Tithe · `world/power_tiers.md:116` · RESOLVED: age recorded, no mechanics; the Tithe of years is removed (D-014)
- G-06 · Tier cap per region for `introduce_npc`; only factions state a highest tier · `world/factions.md:16-72`, `world/geography.md` · RESOLVED: Ford Reaches residents at most Tier 3 (`world/geography.md`)
- G-07 · Rate at which global clocks advance with elapsed time · `world/factions.md:78` · RESOLVED: one segment per season, plus one when neglected (`world/factions.md`)
- G-08 · Reward tables: XP per kind, Standing delta per kind, damage per outcome and effect, coin and item bounds per tier (ENG-09) · `docs/architecture.md` section 6 · open: numbers are engine data, tuned in M1 against D-014 pacing
- G-09 · Calendar detail: month names and lengths, season boundaries, day length, needed for `advance_time` (ENG-11) · `world/00_overview.md:30` · RESOLVED: calendar drafted (`world/00_overview.md`)
