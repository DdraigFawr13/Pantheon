# Canon gaps

Rules or facts the engine needs that `world/` does not settle. Never fill one silently: the owner answers, the answer goes into `world/` in a `canon:` commit (WLD-03), and the line here is marked RESOLVED with the commit.

Format: `- G-<n> · <gap> · <where it shows> · <status>`

- G-01 · Skill rank cap at Tier 0 · `world/power_tiers.md:23` starts at Tier 1, but every Origin grants rank 1 at Tier 0 (`world/protagonist_seed.md:23-25`) · open
- G-02 · How Level 0 becomes Level 1, and what happens if the player refuses both offers · `world/protagonist_seed.md:14`, `:44` · open
- G-03 · Oath count above Tier 2 ("one additional Oath per two tiers after that": Tier 4 or Tier 3?) · `world/power_tiers.md:84` · open
- G-04 · What a "hostile round" is for Last Breath marks · `world/power_tiers.md:123` · open
- G-05 · Character age, needed for the "years of life" Tithe · `world/power_tiers.md:116` · open
- G-06 · Tier cap per region for `introduce_npc`; only factions state a highest tier · `world/factions.md:16-72`, `world/geography.md` · open
- G-07 · Rate at which global clocks advance with elapsed time · `world/factions.md:78` · open
- G-08 · Reward tables: XP per kind, Standing delta per kind, damage per outcome and effect, coin and item bounds per tier (ENG-09) · `docs/architecture.md` section 6 · open
- G-09 · Calendar detail: month names and lengths, season boundaries, day length, needed for `advance_time` (ENG-11) · `world/00_overview.md:30` · open
