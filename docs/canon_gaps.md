# Canon gaps

Rules or facts the engine needs that `world/` does not settle. Never fill one silently: the owner answers, the answer goes into `world/` in a `canon:` commit (WLD-03), and the line here is marked RESOLVED with the commit. Resolved entries name files and sections, not line numbers, because canon lines move.

Format: `- G-<n> · <gap> · <where it shows> · <status>`

- G-01 · Skill rank cap at Tier 0 · `world/power_tiers.md` Skills; Origins in `world/protagonist_seed.md` · RESOLVED `3085d96`: Tier 0 skill cap 1; the Unwritten's cap is their highest affinity rank (D-013)
- G-02 · How Level 0 becomes Level 1, and what happens if the player refuses both offers · `world/protagonist_seed.md` · RESOLVED `3085d96`: the first Oath sets Level 1; refusing both keeps the player Unwritten
- G-03 · Oath count above Tier 2 · `world/power_tiers.md` Oaths · RESOLVED `3085d96`: Oaths at Tiers 1, 2, 4 and 6 (D-010)
- G-04 · What a "hostile round" is for Last Breath marks · `world/power_tiers.md` Death · RESOLVED `3085d96`: a hostile round is a combat exchange
- G-05 · Character age, needed for the "years of life" Tithe · `world/power_tiers.md` · RESOLVED `3085d96`: age recorded, no mechanics; the Tithe of years is removed (D-014)
- G-06 · Tier cap per region for `introduce_npc` · `world/geography.md`, `world/factions.md` · RESOLVED `3085d96`: Ford Reaches residents at most Tier 3
- G-07 · Rate at which global clocks advance with elapsed time · `world/factions.md` Clocks · RESOLVED `3085d96`: one segment per season, plus one when neglected
- G-08 · Reward tables: XP per kind, Standing delta per kind, damage per outcome and effect, coin and item bounds per tier (ENG-09) · `docs/architecture.md` section 6 · open: numbers are engine data, tuned in M1 against D-014 pacing
- G-09 · Calendar detail: month names and lengths, season boundaries, day length (ENG-11) · `world/00_overview.md` · RESOLVED `3085d96`: calendar drafted
- G-10 · Do the Unwritten have a Ledger, and if not, how do they know their own affinities and skills? The UI status panel is drawn from state either way (NAR-04); the question is what the narrator may say · `world/00_overview.md` (the Ledger), `world/power_tiers.md` The Unwritten · open. The opening's last line now says "if an Oath was sworn" (PR #7)
- G-11 · Nine Tier 6 Sovereigns and three Tier 7 Heirs exist in the tier table but no file names or places one. Are they known, hidden or unaligned, and may the narrator introduce one? · `world/power_tiers.md` tier table · open
- G-12 · The cults "the Ironwrit" (Kaul) and "the Turning" (Ysmere) are named once and defined nowhere · `world/pantheon.md` · open
- G-13 · No list of mundane skills, though Origins grant Lore, Streetwise and Ritual · `world/protagonist_seed.md` Origins, `world/power_tiers.md` Skills · open
- G-14 · No list of check categories ("Wilds checks", "stealth in the wild", balance, swimming, sailing), which Oath perks and people traits modify · `world/power_tiers.md` Oaths, `world/peoples.md` · open
- G-15 · Rest and shrines: how long a rest takes, where it is allowed, what a shrine is and where the shrines are, though pool refill and respawn depend on them · `world/power_tiers.md` pools and Death · open
- G-16 · The Unwritten and professions: professions are taken "at awakening", which the Unwritten never have · `world/power_tiers.md` Professions and The Unwritten · open
- G-17 · The Sunken Stair's affinity (rifts "usually" have one) · `world/geography.md`, `world/power_tiers.md` Shards and rifts · open: set in the M3.5 rift batch
- G-18 · "A Rare or better Life skill" cures an Injury: a skill of the Life affinity, or a profession skill? · `world/power_tiers.md` Overspending · open
- G-19 · Road distances do not say on foot or mounted · `world/geography.md` Nearby travel · open
- G-20 · Deferred by canon to data or later: the evolution tree, sub-affinities, each god's second and third Oaths, the steps of people traits · `world/power_tiers.md`, `world/peoples.md` · open: scheduled for M3.5 and after the first version (D-015)
- G-21 · Sea travel at 1,000 km per day on a 2,400 km continent · `world/00_overview.md` Travel · RESOLVED in PR #7: assumed a typo, now 100 km per day; owner confirms at merge
- G-22 · Starting stats reach 35 (array plus +3 and +2) but the Tier 0 typical range was 15 to 30 · `world/protagonist_seed.md`, `world/power_tiers.md` tier table · RESOLVED in PR #7: Tier 0 range widened to 15 to 35; owner confirms at merge
