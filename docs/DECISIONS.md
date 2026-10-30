# Decisions

Settled rules for this project. Not a changelog: an entry stays while the rule is in force. Change a rule here in the same change that changes the behaviour. Mark ideas Proposed until the owner approves them; mark retired entries SUPERSEDED with a pointer, never delete them. Agent assumptions made while building the approved spec use Status "Assumed" (see AGENTS.md).

The requirements themselves live in `docs/SPEC.md` section 2 and the technology choices in its section 3; this file does not copy them.

## D-001 Adopt AI-Master-Instructions (core + game)

- **Status:** Accepted (2026-10-30)
- **Decision:** Pin AI-Master-Instructions v0.5.0 with layers `core` and `project-types/game` in `.ai-master.json`. No stack layer: the master has none for Python. No overrides.
- **Why:** owner asked to integrate the master. `game` covers seeded determinism, one rules engine and AI text never deciding outcomes, which match SPEC ENG-01 to ENG-03. `creative-writing` was not added: project types are used one at a time and Pantheon's canon governance is already in SPEC (WLD-01 to WLD-03).

## D-002 The build spec moves from CLAUDE.md to docs/SPEC.md

- **Status:** Accepted (2026-10-30)
- **Decision:** `CLAUDE.md` holds only `@AGENTS.md` and `@.claude/master/RULES.md`. The spec text is unchanged except paths (`docs/decisions.md` became `docs/DECISIONS.md`). AGENTS.md carries the spec rules every session needs and points to SPEC for the rest.
- **Why:** the master's start-up budget is 200 lines and 24 KB for everything CLAUDE.md loads; the 109-line spec plus 95 lines of shared rules exceeded the line budget, and most of the spec is needed only at milestone start (CTX-06).

## D-003 CI is a drift check until M0

- **Status:** Accepted (2026-10-30)
- **Decision:** `ci.yml` runs only `node .claude/master/sync.mjs --check`. M0 adds uv, ruff, mypy and pytest steps to the same job. Only `docs/**` and `README.md` skip CI; `world/**` does not, because the M0 loader validates canon frontmatter.
- **Why:** no Python project exists yet. The master template skips all `**/*.md`, which would skip canon changes and synced rule changes.

## D-004 `hypothesis` generates action sequences, not seed batteries

- **Status:** Assumed (2026-10-30)
- **Decision:** Engine invariant tests (replay equivalence, bounds) use `hypothesis` to generate action sequences. Determinism (ENG-03) is one fixed-seed test.
- **Why:** reconciles `docs/roadmap.md:21` with GAME-06. See audit item 20.

## D-005 The engine sizes XP, Standing and damage; the narrator chooses other rewards

- **Status:** Accepted (2026-10-30)
- **Decision:** The narrator names the kind of an XP, Standing or damage change and the engine sets the number from a rules table. Items, coin, information and favours are the narrator's choice within engine bounds. Recorded as ENG-09.
- **Why:** owner's answer to audit item 1. Keeps "the engine owns the numbers" (GAME-03) where drift hurts progression most, without making every reward a table entry.

## D-006 Audit fixes applied to the design

- **Status:** Accepted (2026-10-30)
- **Decision:** Audit items 2 to 12 and 20 to 22 are applied to `docs/SPEC.md` (ENG-06, ENG-08 to ENG-11, NAR-03, NAR-04, NAR-07, pytest-cov, import test), `docs/architecture.md` sections 3 to 10, `prompts/narrator.md`, `config.example.toml` and `docs/roadmap.md`. Canon gaps (items 13 to 19) are listed in `docs/canon_gaps.md`, not filled.
- **Why:** owner asked for the audit fixes to be made. Item 9 (model unavailable) follows the recommendation, an engine-rendered fallback turn (NAR-07), so GAME-03 needs no override.

## D-007 Design rounds 2026-10-30

- **Status:** Accepted (2026-10-30)
- **Decision:** The owner settled the design through five form rounds (round 1, review and round 2, two superseded final pages, round 3, final plan). Links are in `docs/HANDOFF.md`. Entries D-008 to D-016 record the outcome; the canon text is in `world/`.
- **Why:** planning-interview skill; one home per fact (SRC-01).

## D-008 Power system: a LitRPG System with d100 checks

- **Status:** Accepted (2026-10-30)
- **Decision:** The Ledger is a LitRPG System: base classes (the 8 former Callings) that evolve at each Ascension Trial; five stats with class gains and 1 free point per level; health, mana and stamina; 15 basic and 5 rare affinities whose rank caps skill rank; skills with rarity (Common to Divine) and rank; skill and affinity shards from rifts; professions; titles. Checks are d100 (ENG-04). Removed: Strain, the Tithe of years, lifespan and age costs, Scars, and the Arts/Mantle/Miracle/Verse/Domain ladder. Rules: `world/power_tiers.md`.
- **Why:** the owner wanted a richer but simpler, Primal Hunter-style base with shards and rifts, no costs paid in time, and room for god-level power. The two earlier designs (Strain-based, lifespan-based) were rejected. The par-relative stat edge keeps same-tier checks fair at every tier (a plain stat term reached 93 % at Tier 7).

## D-009 Overspending risks a permanent Injury

- **Status:** Accepted (2026-10-30)
- **Decision:** Mana or stamina may go up to 50 % below zero; afterwards a d100 roll at 2 % per 1 % overspent gives a permanent Injury, curable only by Rare+ Life skills or high-grade alchemy.
- **Why:** owner's round 3 note. Gives Life and alchemy a purpose.

## D-010 Affinities, gods and Oaths

- **Status:** Accepted (2026-10-30)
- **Decision:** Basic: Flame, Frost, Tide, Storm, Wind, Stone, Iron, Growth, Beast, Light, Shadow, Life, Death, Mind, Song. Rare: Binding, Space, Blood, Spirit, and one sealed. Each god favours two (Veshra Binding/Mind, Kaul Iron/Flame, Ysmere Tide/Life, Maru-Ghen Death/Stone, Ilvane Light/Space, Drovash Shadow/Wind, Hurrow Beast/Growth). An Oath is a blessing (+1 affinity rank, one perk) with one Burden; a Breach suspends the blessing and costs 20 Standing until atoned. Oaths at Tiers 1, 2, 4 and 6. Any class may swear any Oath; favoured classes get +5 with that god's affinities. Each god will offer 2 to 3 Oaths (after the first version). Sub-affinities later.
- **Why:** owner's answers (round 3: more affinities; final plan: Fate replaced by Space).

## D-011 Peoples, professions, rifts

- **Status:** Accepted (2026-10-30)
- **Decision:** Five peoples born of Caldrenne (Humans, Riftborn, Fenfolk, Saltborn, Stonekin), each with an innate affinity, a trait and +3 to a stat; no race levels. Fifteen professions in gathering, crafting and service groups; one at awakening, a second at Tier 3. Delves are renamed rifts everywhere (Delve Tide is now the Rift Tide; flag `rifts_closed`).
- **Why:** owner's answers (round 3 and final plan).

## D-012 Sealed canon

- **Status:** Accepted (2026-10-30)
- **Decision:** The hidden second magic is a sealed rare affinity in `world/sealed/` (WLD-04). Approved outline: a different logic from Oath magic, granted by no god and not tracked by the Ledger the way Oaths are; usable by the player eventually, with or without an Oath; never paid in mana, stamina, time or lifespan, with its own engine-tracked cost; never simply stronger than Oath magic at the same tier; may touch Standing and at most one existing secret thread; may not contradict public canon, break content limits or change the endings; a first trace in the Ford Reaches early in play, not takeable in the first version. A reviewer agent checks content instead of the owner. Sealed entries use neutral ids and the flags `unwritten_path`, `sealed_a_trace_ready` and `sealed_a_trace_seen`, all set by the engine or authored beats.
- **Why:** owner chose "secrets I never read", outline approval, sealed folders, and folding the hidden magic into the affinities.

## D-013 Story rules adopted from the design pass

- **Status:** Accepted (2026-10-30)
- **Decision:** (1) The rival swears the Oath the player refused in the opening. (2) Standing for public deeds and some titles needs a witness; unwitnessed deeds become rumours. (3) Gods send small petitions through Vessels. (4) The Unwritten grow through shards, gear, allies and reputation; their skill cap is their highest affinity rank and their affinity cap is 3.
- **Why:** owner agreed to each proposal.

## D-014 Pacing, time and death

- **Status:** Accepted (2026-10-30)
- **Decision:** Tier 2 in about 8 hours of play; each later tier about 1.5 times the last (XP rewards scale with tier; numbers are engine data tuned in M1). A session covers about a week in-world. Clocks advance one segment per season, plus one more when neglected for a season. Reckonings escalate and the fourth death is final. Age is recorded (start 16 to 30) with no mechanics. Combat runs in exchanges with enemy intents shown; deeper tactics come right after the first version.
- **Why:** owner's answers in rounds 1 to 3.

## D-015 First version scope and phone play

- **Status:** Accepted (2026-10-30)
- **Decision:** First playable version (through M3.5): the Ford Reaches, Tier 0 to Tier 2, the opening, bounties, crafting and professions, one rival, the first rift, the Unwritten path, the sealed affinity's first trace. A minimal phone web page arrives at M2.5. After: tactical combat, sub-affinities, full Oath list, codex and journal, romance (Standing plus flags), companions, holdings, prophecy, images (off until the owner sets a monthly cap).
- **Why:** owner's keep list and final plan.

## D-016 Content limits

- **Status:** Accepted (2026-10-30)
- **Decision:** Allowed: romance, off-screen sexual content, torture, slavery and debt-bondage, real-world religious parallels. Not allowed: harm to children, body horror.
- **Why:** owner's round 1 answer.

## D-017 The opening's two gods are drawn at random

- **Status:** Accepted (2026-10-30)
- **Decision:** At timeline creation the engine draws two of the seven gods from the timeline's seed and records an `opening_gods_drawn` event; each offers its first Oath. The rival swears the refused god's Oath (D-013). A config setting may fix the pair for tests.
- **Why:** owner wants restarts to open different paths. Seeded, so replays and forks stay deterministic (ENG-03).

## D-018 Plan changes are shown to the owner as an artifact

- **Status:** Accepted (2026-10-30)
- **Decision:** Every change to `docs/BUILD_PLAN.md` or `docs/roadmap.md` is rendered by `scripts/render_plan.py` and republished to one standing artifact (https://claude.ai/artifact/HkerL2UNT7oeQcFPW2dZmy), linked in the same reply. The repo files stay the source of truth; the page is a view.
- **Why:** owner's instruction, 2026-10-30. The owner reviews from a phone; a rendered page is easier to read than Markdown in a diff.

## D-019 Libraries approved: PyYAML, anthropic, uvicorn, jinja2

- **Status:** Accepted (2026-10-30)
- **Decision:** Add PyYAML (MIT, M0), anthropic (Apache-2.0, M2), uvicorn (BSD-3-Clause, M2.5) and jinja2 (BSD, M2.5). All are free; the only running cost is model usage.
- **Why:** owner approved, 2026-10-30. Licences checked on PyPI the same day.

## D-020 Local models through Ollama

- **Status:** Accepted (2026-10-30)
- **Decision:** Support a local Ollama server as a second narrator backend by pointing the Anthropic SDK at Ollama's Anthropic-compatible API (no new dependency). Choose the default narrator after a side-by-side scripted test in M2.
- **Why:** owner asked about free models. Ollama is MIT-licensed and runs models at no per-turn cost, but needs a capable machine (about 16 GB RAM for 8B models; about 24 GB of GPU memory for the 24 to 27B models reported to narrate well) and lacks prompt caching, `count_tokens` and `tool_choice` (docs.ollama.com/api/anthropic-compatibility).

## D-021 The game runs on the owner's Windows gaming PC

- **Status:** Accepted (2026-10-30)
- **Decision:** The game (and Ollama, per D-020) runs on the owner's Windows gaming PC, started by a one-click `start.bat`. The phone reaches the page over home Wi-Fi first; Tailscale (free personal plan) adds access away from home without exposing anything to the public internet, so the page needs no login. Python code must run on Windows as well as Linux (CI and cloud sessions).
- **Why:** owner chose their PC and asked to go with the recommendations. Cloud sessions cannot attach to a Windows computer, so on-PC checks (GPU, playtests) are done by the owner or a local Claude Code session.

## D-022 Patterns adopted from Andromeda

- **Status:** Assumed (2026-10-30)
- **Decision:** Adopt, as our own code, four patterns seen in the open-source Andromeda RPG (MIT code, github.com/danielrod36/Andromeda, read 2026-10-30): named RNG streams; a validate-roll-mutate-append command funnel where a rejected command consumes no randomness; a curated state view for the narrator prompt; a banned-mechanical-terms list in the prose validator. No code is copied; if any is, it is credited in `docs/ATTRIBUTION.md` with its MIT notice (SAFE-05). Not adopted: their JSON-snapshot reload (we replay the event log, ENG-06), no prompt caching, and their read-only narrator (ours proposes state changes through tools).
- **Why:** each pattern makes determinism or narrator safety stronger at no extra dependency. Andromeda is the closest public design to Pantheon found in the 2026-10-30 research.

## D-023 M0 implementation assumptions

- **Status:** Assumed (2026-10-30)
- **Decision:** (1) The loader skips `README.md` files; every other Markdown file under `world/` must carry frontmatter. (2) The import-boundary test also keeps `memory` and `storage` out of `engine/`, stricter than SPEC section 4. (3) pytest treats warnings as errors. (4) CI runs one Linux job on every PR; the Windows job runs only from "Run workflow" (Tier 3), since Windows runners cost more and the game's Windows use is checked on the owner's PC. (5) Names-only data tables in `world/data/` (gods, affinities, Oaths, classes, peoples, professions) are canon and are checked against the prose.
- **Why:** M0 needed these choices to pass its acceptance criteria; none changes a requirement.

## D-024 Flag registry, loader exclusions and the sealed-path guard

- **Status:** Accepted (2026-10-30; owner: "fix the three M0 blockers, then do whatever you recommend")
- **Decision:** (1) Every flag that a reveal gate, beat or canon file names is listed in `world/data/flags.yaml`, or in `world/sealed/data/flags.yaml` for sealed flags, with its `kind` (`bool` or `counter`), who sets it (`engine`, `beat`, `narrator`) and, for narrator flags, an `accept` rule. Gates read only registered flags and state fields (NAR-02). The narrator may set other keys only under `story.`, true or false. (2) Destroying a rift's core is `grant_loot` from `rift_core:<id>` after a successful check; it emits `rift_closed`, which counts `flags.rifts_closed`. (3) The loader fails when the sealed type and the `world/sealed/` path disagree (WLD-04). The loader enforces (1) and (3), and `tests/world/test_flags.py` checks every gate path. README files and the root-only `/data/` ignore are already in D-023 and PR #8.
- **Why:** audit `docs/audit/2026-10-30-repo-audit.md` items 1 to 3 and 11: six gate flags had no setter, so three secrets could never release; the sealed README would fail the M0 load; canon tables would have been silently ignored by git.

## D-025 Second-pass audit fixes to the design

- **Status:** Accepted (2026-10-30; same owner instruction as D-024)
- **Decision:** Applied audit items 4, 6 to 10, 12 and 18 (item 17, Windows CI, is settled by D-023 point 4) to `docs/SPEC.md`, `docs/architecture.md`, `docs/BUILD_PLAN.md`, `docs/KICKOFF_PROMPT.md`, `config.example.toml` and `scripts/render_plan.py`. In short: every reply that will be recorded passes the NAR-04 validator, and the fallback text replaces prose that still fails; `advance_clock` stays (canon allows it, `world/factions.md`) but must cite a `check_id` or `beat_id` the clock's data lists, one segment, at most once per clock per in-world day; `burden_tested` keeps the narrator's `situation` and the UI shows it; `base_url` is in the example config (D-020).
- **Why:** each rule the engine was asked to enforce must be computable from state (ENG-02), and each consequence visible to the player (GAME-04).

## D-026 Cloud sessions reuse the harness branch name

- **Status:** Accepted (2026-10-30)
- **Decision:** Claude Code cloud sessions push to the branch name the harness assigns, which can repeat across PRs. After a merge the branch is cut again from the latest `main` before new work, so no merged history is reused. This meets GIT-01's intent; it is not an override.
- **Why:** PRs #1 to #6 shared one branch name (audit item 13). The harness assigns the name; recording the practice stops a later session from treating it as a GIT-01 breach.
