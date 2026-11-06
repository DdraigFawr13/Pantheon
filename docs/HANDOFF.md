# Handoff

Updated: 2026-11-06. A fresh session must be able to continue from this file alone. Keep it to 60 lines; move finished entries to `docs/archive/handoff-YYYY-MM.md`.

## Phase

M1.7 (D-041) and the 25-class roster (D-042) merged as PR #18. M1a to M1c are merged. PR #20 (master v4.11.0, D-043, two audits) and PR #21 (every audit finding fixed or recorded; the play guard denies by default, D-044) are merged. Still open from the audit: canon gaps G-28 to G-32 (the owner answers them); MEM-01 to MEM-04 have no tests until M3.

**M1 is complete: M1d, M1e and M1f merged as PR #19** (owner approved 2026-11-06), which brought in #16 (D-039); #16 is closed as superseded. **Next: M2 (narrator loop)**, starting with an M1 audit offer (VER-09) and the owner's playtest with a fight.

## Just done

- 2026-11-03 Master upgrade to v4.4.0 (D-040), PR #17 merged.
- 2026-11-06 Master upgrade to v4.11.0 (D-043) and the repo and tests audits, PR #20 merged; audit fixes, PR #21 merged.
- 2026-11-06 M1.7 (D-041): `pantheon session` runs each turn step as a command; `/play` skill; `play-guard` hook (Bash only `uv run pantheon session` and `scripts/saves.sh`, public reads only); saves as a text dump on the `saves` branch; the Pantheon Table page (https://claude.ai/artifact/WoBEwUTajnMQTrPV1NBJ3b) shows story, Character, Journal and Gear tabs from `session screen` JSON and sends taps to the session as comments.
- 2026-11-06 D-042: 25 base classes with traits and blurbs (`world/data/classes.yaml`, power_tiers.md table, gods' favoured classes); `class-design` skill; roster page https://claude.ai/artifact/96Gk7pos2FRTar4ezcyRfS.
- 2026-11-06 First session play, five turns: `docs/playtests/2026-11-06-session-play.md`. The owner: "the game works and the fundamentals are fun", the writing needs work and maybe shortening to move quicker ("we can get to that later"). Ddraig Fawr (he/him), Elementalist attuned to Storm, Enchanter, sworn to Ysmere; timeline `ddb27b36` on the `saves` branch.
- 2026-11-06 M1d on PR #19: #16 merged in (its tests moved from the cut Wager-bound to Warden). Nine solo fight traits (D-045) as data in `world/data/combat.yaml` `traits`, read by `engine/traits.py`, through `CheckRequest.bonus`; `choose attunement <element>`. Session play runs fights (a picked fight option rolls first, a Downed turn runs by itself, `session tool --file`). LitRPG direction (D-046).
- 2026-11-06 M1e on PR #19 (D-047, the owner's numbers, XP 15 % above the first draft): tier-scaled XP, foe XP and body loot, `grant_loot`, `adjust_inventory`, `adjust_currency`, five canon items, gear and tonics, `session use/equip/unequip`. `scripts/pacing_sim.py` estimates 7.0 h to Tier 2, so D-014 says about 7. M1f: `pantheon roll`, `sheet`, `log`. Game page: fight panel, Gear tab, Codex tab with sub-tabs and search. Scripted check: `docs/playtests/2026-11-06-m1-fight-check.md`.

## Next

1. New branch from `main` for the next unit of work (GIT-01). Offer the owner an M1 audit (VER-09) before M2. Then read BUILD_PLAN "M2: Narrator loop" and mark what M1.5 to M1.7 already built.
2. Owner plays a session with a fight: `choose attunement storm` comes first (the story already says Storm). Watch foe XP (two levels from one early fight in the scripted check) and loot rates.
3. Record the turn-5 sack hook (Tam says the humming sack brought the Stair down; do not open it) at the start of the next play turn.
4. Offer an audit of M1 (VER-09). Next milestone in the plan: M2 (narrator loop), much of which M1.5 to M1.7 built.
5. Known gaps: foe tables (G-33), more Tier 1 items (G-34), Codex descriptions (G-35); `pantheon play` (API path) has no gear commands; Attuned does not require the element's affinity.

## Open questions

- Prose length and pace: the owner may want shorter scenes (D-033 says 200 to 400 words). Ask before changing D-033.
- Reward, loot and evolution numbers are engine data to tune (G-08). What does training give (G-27)?
- Do the D-038 clock rates hold in play?
- Owner answers gaps G-10 to G-20 before the M3.5 content batches (`docs/canon_gaps.md`).

## Plan page (D-018)

- https://claude.ai/artifact/HkerL2UNT7oeQcFPW2dZmy: republish whenever the plan or roadmap changes.

## Design forms (owner's answers live in each page's database)

- Round 1: https://claude.ai/artifact/JSEqjnAXHhNCrWkR4fXdwQ
- Review and round 2: https://claude.ai/artifact/RcPLtGKcnpqMVpqvQLtUtQ
- Superseded final check: https://claude.ai/artifact/YQjWtqPffUopaDLGUJ7Ysg
- Round 3 (the System): https://claude.ai/artifact/BwmhqfG5VXYAoR2hd4QwfC
- Final plan (approved): https://claude.ai/artifact/4uyMuu6Xa6dHD2Y9fXQa1s
- Style round 1: https://claude.ai/artifact/5fnPKcTrTudPap9ozbqjTV
- Style round 2 (approved): https://claude.ai/artifact/3yHuM5FmjjJ7Pee81qzgnc

## Decisions since the last plan update

- 2026-11-06 D-007 to D-047 in `docs/DECISIONS.md` (D-022, D-023, D-027, D-028, D-030, D-031, D-037 to D-039, D-045 Assumed).
