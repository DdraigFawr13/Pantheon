# Handoff

Updated: 2026-11-06. A fresh session must be able to continue from this file alone. Keep it to 60 lines; move finished entries to `docs/archive/handoff-YYYY-MM.md`.

## Phase

M1.7 and D-042 are merged (PR #18). **M1d is built on draft PR #19, branch `claude/m1-build`**, which merges #16 (D-039) onto main and supersedes it. Next: M1e, then M1f, on the same branch.

## Just done

- 2026-11-03 Master upgrade to v4.4.0 (D-040), PR #17 merged.
- 2026-11-06 M1.7 (D-041): `pantheon session` runs each turn step as a command; `/play` skill; `play-guard` hook (Bash only `uv run pantheon session` and `scripts/saves.sh`, public reads only); saves as a text dump on the `saves` branch; the Pantheon Table page (https://claude.ai/artifact/WoBEwUTajnMQTrPV1NBJ3b) shows story, Character, Journal and Gear tabs from `session screen` JSON and sends taps to the session as comments.
- 2026-11-06 D-042: 25 base classes with traits and blurbs (`world/data/classes.yaml`, power_tiers.md table, gods' favoured classes); `class-design` skill; roster page https://claude.ai/artifact/96Gk7pos2FRTar4ezcyRfS.
- 2026-11-06 First session play, five turns: `docs/playtests/2026-11-06-session-play.md`. The owner: "the game works and the fundamentals are fun", the writing needs work and maybe shortening to move quicker ("we can get to that later"). Ddraig Fawr (he/him), Elementalist attuned to Storm, Enchanter, sworn to Ysmere; timeline `ddb27b36` on the `saves` branch.
- 2026-11-06 M1d on PR #19: #16 merged in (only doc conflicts; its tests moved from the cut Wager-bound to Warden). The owner chose the nine solo fight traits (D-043): data in `world/data/combat.yaml` `traits`, read by `engine/traits.py`, a `bonus` on `CheckRequest` so odds and roll agree, `choose attunement <element>` for the Elementalist. Session play runs fights: a picked fight option rolls `fight_move` before the prose, a Downed turn runs the foes' exchange, `session tool --file`, a /play Fights section, and a fight panel on the game page (republished, version 8). Owner's direction: LitRPG pacing and tone (D-044).

## Next (the M1 build session)

1. **M1e rewards and loot** on `claude/m1-build`: `world/data/rewards.yaml` and Tier 1 loot tables (ENG-09, G-08); items, coin changes and an inventory, so the page's Gear tab shows real things; the pacing simulation script. Tune to D-044 inside D-014. Canon numbers need the owner's approval and `canon:` commits.
2. **M1f dev CLI:** `pantheon roll`, `pantheon sheet`, `pantheon log`.
3. The owner's save (Ddraig, Elementalist) will be asked `choose attunement` first; the story already says Storm.
4. Record the turn-5 sack hook (Tam says the humming sack brought the Stair down; do not open it) at the start of the next play turn.
5. After M1: report requirements met, deferred and defects; offer an audit (VER-09); republish the plan page (D-018); a playtest with a fight to `docs/playtests/`.

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

- 2026-11-06 D-007 to D-044 in `docs/DECISIONS.md` (D-022, D-023, D-027, D-028, D-030, D-031, D-037 to D-039, D-043 Assumed).
