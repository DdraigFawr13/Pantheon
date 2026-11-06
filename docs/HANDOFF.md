# Handoff

Updated: 2026-11-06. A fresh session must be able to continue from this file alone. Keep it to 60 lines; move finished entries to `docs/archive/handoff-YYYY-MM.md`.

## Phase

M1.7 (D-041) and the 25-class roster (D-042) merged as PR #18. M1a to M1c are merged. PR #20 (master v4.11.0, D-043, two audits) and PR #21 (every audit finding fixed or recorded; the play guard denies by default, D-044) are merged. Still open from the audit: canon gaps G-28 to G-32 (the owner answers them); MEM-01 to MEM-04 have no tests until M3.

**M1 is complete: M1d, M1e and M1f merged as PR #19** (owner approved 2026-11-06), which brought in #16 (D-039); #16 is closed as superseded. **M2 (narrator loop) is planned** (D-051, D-052): four parts, M2a first, then the owner plays a session with a fight.

D-048: a due hook or a moved clock always gets one suggested action leading back to it (prompt rule; M4's beat scheduler enforces it later). D-050 (design audit F3): no option menu outside fights; the closing thought carries the odds, a typed action that rolls is previewed first (`session go`); the owner may move to preview-only (shape A) later. Mock-up: https://claude.ai/artifact/8jXbpgTg7zXjRk7bhfWZxb

## Just done

- 2026-11-06 Design audit of M1d to M1f (owner chose design only): `docs/audit/2026-11-06-design.md`, 28 findings (3 strongly recommended: M2 plan stale, architecture section 3 stale, tapped options undecided). PR #23. Owner: "Do as you recommend": all 28 accepted (D-049); 23 fixed in e9f2a6f. Re-run pacing sim: 9.9 h to the Tier 2 Trial against D-014's 7 h target, median fight 6 exchanges (estimates; owner's fight playtest decides any retune).

- 2026-11-06 Master upgrade to v4.11.0 (D-043) and the repo and tests audits, PR #20 merged; audit fixes, PR #21 merged.
- 2026-11-06 M1.7 (D-041): `pantheon session` runs each turn step as a command; `/play` skill; `play-guard` hook (rules: D-044 (1)); saves as a text dump on the `saves` branch; the Pantheon Table page (https://claude.ai/artifact/WoBEwUTajnMQTrPV1NBJ3b) shows story, Character, Journal and Gear tabs from `session screen` JSON and sends taps to the session as comments.
- 2026-11-06 D-042: 25 base classes with traits and blurbs (`world/data/classes.yaml`, power_tiers.md table, gods' favoured classes); `class-design` skill; roster page https://claude.ai/artifact/96Gk7pos2FRTar4ezcyRfS.
- 2026-11-06 First session play, five turns: `docs/playtests/2026-11-06-session-play.md`. The owner: "the game works and the fundamentals are fun", the writing needs work and maybe shortening to move quicker ("we can get to that later"). Ddraig Fawr (he/him), Elementalist attuned to Storm, Enchanter, sworn to Ysmere; timeline `ddb27b36` on the `saves` branch.
- 2026-11-06 M1d on PR #19: #16 merged in (its tests moved from the cut Wager-bound to Warden). Nine solo fight traits (D-045) as data in `world/data/combat.yaml` `traits`, read by `engine/traits.py`, through `CheckRequest.bonus`; `choose attunement <element>`. Session play runs fights (a picked fight option rolls first, a Downed turn runs by itself, `session tool --file`). LitRPG direction (D-046).
- 2026-11-06 M1e on PR #19 (D-047, the owner's numbers, XP 15 % above the first draft): tier-scaled XP, foe XP and body loot, `grant_loot`, `adjust_inventory`, `adjust_currency`, five canon items, gear and tonics, `session use/equip/unequip`. `scripts/pacing_sim.py` estimates 7.0 h to Tier 2, so D-014 says about 7. M1f: `pantheon roll`, `sheet`, `log`. Game page: fight panel, Gear tab, Codex tab with sub-tabs and search. Scripted check: `docs/playtests/2026-11-06-m1-fight-check.md`.

## Next

1. Audit fixes merged as PR #24 (owner approved 2026-11-06).
2. **M2a merged as PR #27** (owner approved 2026-11-06): only Hard or harder checks stop at the preview (NAR-08); scenes are 150 to 250 words (`SCENE_LENGTH`). The owner's playtest moves to after M2d (D-052, amended). **M2b in progress** on branch `m2b-reliability`: spec `docs/specs/m2b-reliability.md` (assumptions D-053). S1 done (session play: 3 tries per tool and prose, dropped-call events, fallback turn; the API loop now tries the third call). S2 done (`engine/preview.py` for both paths; `pantheon play` has no list outside fights, stamps closing-thought odds, previews Hard checks, numbers the Dual Offer from 1). Next: S3 (10-turn scripted runs on both paths), then a fresh reviewer against the spec and a draft PR.
3. After M2d, the owner plays a session with a fight: `choose attunement storm` comes first (the story already says Storm). Watch foe XP (two levels from one early fight in the scripted check) and loot rates.
4. Record the turn-5 sack hook (Tam says the humming sack brought the Stair down; do not open it) at the start of the next play turn.
5. Known gaps: foe tables (G-33), more Tier 1 items (G-34), Codex descriptions (G-35); `pantheon play` (API path) has no gear commands; Attuned does not require the element's affinity.

## Open questions

- Pace: 9.9 h to Tier 2 against D-014's 7 h (estimate, D-047 (8)); the owner's fight playtest decides, with no preferred lever yet.
- Reward, loot and evolution numbers are engine data to tune (G-08). What does training give (G-27)?
- Do the D-038 clock rates hold in play?
- Owner answers gaps G-10 to G-20 before the M3.5 content batches (`docs/canon_gaps.md`).

## Plan page (D-018)

- https://claude.ai/artifact/HkerL2UNT7oeQcFPW2dZmy: republish whenever the plan or roadmap changes.

## Design forms (owner's answers live in each page's database)

- M2 round 1: https://claude.ai/artifact/S1M8kTeHdi6pX1njM7FXvA
- M2 review and round 2 (approved in chat): https://claude.ai/artifact/LcHA2Zu4vbVaX4jYuhdBEP

- Round 1: https://claude.ai/artifact/JSEqjnAXHhNCrWkR4fXdwQ
- Review and round 2: https://claude.ai/artifact/RcPLtGKcnpqMVpqvQLtUtQ
- Superseded final check: https://claude.ai/artifact/YQjWtqPffUopaDLGUJ7Ysg
- Round 3 (the System): https://claude.ai/artifact/BwmhqfG5VXYAoR2hd4QwfC
- Final plan (approved): https://claude.ai/artifact/4uyMuu6Xa6dHD2Y9fXQa1s
- Style round 1: https://claude.ai/artifact/5fnPKcTrTudPap9ozbqjTV
- Style round 2 (approved): https://claude.ai/artifact/3yHuM5FmjjJ7Pee81qzgnc

## Decisions since the last plan update

- 2026-11-06 D-007 to D-052 in `docs/DECISIONS.md` (D-022, D-023, D-027, D-028, D-030, D-031, D-037 to D-039, D-045 Assumed).
