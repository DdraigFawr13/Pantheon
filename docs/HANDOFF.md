# Handoff

Updated: 2026-11-06. A fresh session must be able to continue from this file alone. Keep it to 60 lines; move finished entries to `docs/archive/handoff-YYYY-MM.md`.

## Phase

M1.7 (D-041) and the 25-class roster (D-042) merged as PR #18. M1a to M1c are merged.

PR #20 merged: master v4.11.0 (D-043) and two audits, `docs/audit/2026-11-06-repo.md` (42 findings) and `docs/audit/2026-11-06-tests.md` (28 findings). The owner accepted every recommendation ("Ok do what you recommend for all").

PR #21 merged: every audit finding fixed or recorded (each report's Outcome names the commit). The play guard denies by default (D-044); 539 tests in 15 s, 98.51 % coverage; mypy strict on all of `src/pantheon`. Still open from the audit: canon gaps G-28 to G-32 (the owner answers them); MEM-01 to MEM-04 have no tests until M3.

**Next: build the rest of M1 (M1d, M1e, M1f) on a new branch cut from `main`.** M1d combat already exists as draft PR #16 (`m1d-combat`, D-039), cut from main before #17 and #18; D-039 exists only on that branch until it merges.

## Just done

- 2026-11-03 Master upgrade to v4.4.0 (D-040), PR #17 merged.
- 2026-11-06 Master upgrade to v4.11.0 (D-043) and the repo and tests audits, PR #20 merged; audit fixes, PR #21 merged.
- 2026-11-06 M1.7 (D-041): `pantheon session` runs each turn step as a command; `/play` skill; `play-guard` hook (Bash only `uv run pantheon session` and `scripts/saves.sh`, public reads only); saves as a text dump on the `saves` branch; the Pantheon Table page (https://claude.ai/artifact/WoBEwUTajnMQTrPV1NBJ3b) shows story, Character, Journal and Gear tabs from `session screen` JSON and sends taps to the session as comments.
- 2026-11-06 D-042: 25 base classes with traits and blurbs (`world/data/classes.yaml`, power_tiers.md table, gods' favoured classes); `class-design` skill; roster page https://claude.ai/artifact/96Gk7pos2FRTar4ezcyRfS.
- 2026-11-06 First session play, five turns: `docs/playtests/2026-11-06-session-play.md`. The owner: "the game works and the fundamentals are fun", the writing needs work and maybe shortening to move quicker ("we can get to that later"). Ddraig Fawr (he/him), Elementalist attuned to Storm, Enchanter, sworn to Ysmere; timeline `ddb27b36` on the `saves` branch.

## Next (the M1 build session)

1. Cut a branch from `main`. Read BUILD_PLAN "M1: Engine core" for M1d to M1f.
2. **M1d combat:** bring PR #16 onto current `main` (merge `main` into `m1d-combat`, resolve, re-run checks; never force-push it, GIT-03), or rebuild it from its diff if that is cleaner. Then add session support: `start_fight`, `fight_move` and `end_fight` in `session tool` and `/play`; a chosen `fight_move` rolls before prose like `request_check`; show foe intents and the fight on the page's screen JSON. D-039 lists what #16 left out.
3. **M1e rewards and loot:** `world/data/rewards.yaml` and Tier 1 loot tables (ENG-09, G-08); items, coin changes and an inventory, so the page's Gear tab shows real things; the pacing simulation script. Canon numbers need `canon:` commits and the owner's approval.
4. **M1f dev CLI:** `pantheon roll`, `pantheon sheet`, `pantheon log`.
5. Class traits (D-042) are text only; decide with the owner which to implement in M1d (combat traits) and which wait.
6. Small fixes found in play: let `session tool` read its JSON from a file (`--file data/tool.json`), so the guard's no-`;` rule and shell quoting stop breaking tool calls; record the turn-5 sack hook (Tam says the humming sack brought the Stair down; do not open it) at the start of the next play turn.
7. After M1: report requirements met, deferred and defects; offer an audit (VER-09); republish the plan page (D-018).

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

- 2026-11-06 D-007 to D-038, D-040 to D-043 in `docs/DECISIONS.md` (D-022, D-023, D-027, D-028, D-030, D-031, D-037, D-038 Assumed).
