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
- **Decision:** Mana or stamina may go up to 50 % below zero; afterwards a d100 roll at 2 % per 1 % overspent gives a permanent Injury, curable only by Rare+ Life skills or high-grade alchemy (what those are is open, G-18; until then no cure is built).
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
- **Decision:** Tier 2 in about 7 hours of play (was 8 until D-047); each later tier about 1.5 times the last (XP rewards scale with tier; numbers are engine data tuned in M1). A session covers about a week in-world. Clocks advance one segment per season, plus one more when neglected for a season. Reckonings escalate and the fourth death is final. Age is recorded (start 16 to 30) with no mechanics. Combat runs in exchanges with enemy intents shown; deeper tactics come right after the first version.
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

## D-027 Ollama runs with a 32,768-token context

- **Status:** Assumed (2026-10-30)
- **Decision:** When the narrator uses Ollama (D-020), the server starts with `OLLAMA_CONTEXT_LENGTH=32768`, set by `start.bat`. The M2 adapter treats a reported input-token count far below its own estimate as a truncated prompt and fails the call; the turn then takes the NAR-07 fallback. The first local model to test is `qwen3:8b`.
- **Why:** the owner's check on 2026-10-30 showed `qwen3:8b` at 100 % GPU on the RX 6700 XT through Vulkan, at the 4,096-token default. Ollama's docs say the default is 4k below 24 GiB of VRAM, and the Anthropic-compatible API has no per-request context option (docs.ollama.com/context-length, /api/anthropic-compatibility, read 2026-10-30). Pantheon's prompt is about 26,000 tokens (a 6,000-token canon prefix plus the 20,000-token MEM-04 budget), so the default would cut most of it. 32,768 tokens covers that with room for the reply. Memory estimate: about 4.5 GiB of fp16 KV cache at 32,768 tokens for `qwen3:8b`, so about 10 GB in total, inside 12 GB; the owner confirms with `ollama ps`.

## D-028 M1a check assumptions

- **Status:** Assumed (2026-10-30)
- **Decision:** (1) A roll of 01 to 05 is always a Triumph: it first succeeds, then upgrades one step, even when the roll is over the chance. (2) A check settled by the tier gap gives plain Success or Failure, with no roll, no complication and no randomness used. (3) The chance is not clamped; a roll of 96 to 00 can succeed when the chance is high enough, as "any outcome" implies. (4) An Overcome claim counts only where it lifts an automatic failure, so it does nothing on a non-force check (G-24). Artifact and Ally need a tier at or above the challenge's (G-23); Divine Favor needs Standing 60 or higher; Oath and Terrain are accepted as claimed, per `docs/architecture.md` section 6. (5) `engine/rng.py` is the dice module; no separate `dice.py`. (6) A negative stat is rejected, so M1b must floor stats at 0 when Injuries apply. Flat bonuses from Oaths, titles and traits arrive with those systems in M1b.
- **Why:** M1a needed these to be testable and canon does not settle them. Each follows the literal wording in `world/power_tiers.md` Checks, and each is one small change if the owner prefers otherwise.

## D-029 Thin narrator loop before the rest of M1

- **Status:** Accepted (2026-10-30; owner: "do what you recommend to get this to that thin narrator loop as a project demo / check and I can see if it is fun")
- **Decision:** After M1a, build a thin vertical slice (milestone M1.5 in `docs/BUILD_PLAN.md`) and play it on the owner's PC before M1b. It has 7 narrator tools, not the audit's 6: `request_check`, `apply_effect`, `grant_xp`, `set_flag`, `register_hook`, `suggest_actions`, plus `adjust_standing` (the gods' reactions need a visible result). The Dual Offer is a player command with a menu, not a narrator tool: in the first live run the model called such a tool on the opening turn and refused both Oaths for the player. Left out until the full milestones: class skills and shards, combat exchanges and death, items, coin changes, the calendar, forks, summaries and FTS5, and streaming prose (the NAR-04 validator must see a reply before the player does).
- **Why:** the audit found that the plan's top risks (narrator obedience, balance) were tested last. Later systems land behind the same tool and event pattern.

## D-030 Thin loop assumptions

- **Status:** Assumed (2026-10-30)
- **Decision:** (1) Reward numbers in `world/data/rewards.yaml` are first guesses: XP minor 25, major 60, milestone 150, at most 200 per turn; Tier 1 levels give +2 primary and +1 secondary; Standing slight 2, notable 5, grave 15; damage is 25 % of maximum HP on a failure, 10 % on a success at cost and 15 % from a named hazard; aid heals 25 %, a rest heals fully. (2) A 0 HP character is only Downed in this slice; Last Breath and death come with M1d. (3) NAR-04 rejects every digit the engine did not return this turn, mechanical terms, and number words beside a unit ("two points"), but not plain number words, since "two voices" is ordinary prose. (4) Replies carry prose and tools; a list of actions written into the prose is cut, and a separate round asks for `suggest_actions` when the model skipped it. (5) A skill the character lacks counts as rank 0 rather than a rejection. (6) `set_flag` rejects the narrator flags whose accept rules need tools this slice lacks (coin spends, NPC introductions). (7) The game talks to a private Ollama server on port 11435, started by `start.bat` with the D-027 context, so the owner's normal Ollama stays untouched.
- **Why:** the slice needs these to be playable. Each is data or one small rule; the owner's playtest decides which to change.

## D-031 The engine runs each turn in three steps

- **Status:** Assumed (2026-10-30)
- **Decision:** A turn is a referee call (only `request_check` counts, thinking off), a narrator call (prose only, told the exact outcome), then a scribe call (`grant_xp`, `apply_effect`, `adjust_standing`, `register_hook`, `set_flag`, `suggest_actions`, thinking off). Every call sends the same tool list and the engine decides which calls count, because the model's template renders tools before the history and a changing list empties its cache. Hooks and Standing changes are limited to 2 each per turn. This replaces the free tool loop in `docs/architecture.md` section 3 for this slice. The prompt puts everything static first and the character sheet and due material in the latest message; history grows from N to 2N-1 turns and then resets (a change to the NAR-01 order; M3 revisits it when lore becomes dynamic).
- **Why:** measured on `qwen3:8b` over 6 live turns with the free loop: 0 checks and 0 XP, and the model decided a contested action itself; about 2 minutes per turn. Rolling before prose makes the story follow the dice. Server logs then showed prompt reading at about 39 tokens per second against about 50 for writing, with 2,000 to 3,000 tokens re-read per call, so cache misses were the main cost.

## D-032 Claude is the default narrator; the local model is rejected for play

- **Status:** Accepted (2026-10-30; owner: "we just need to use a cheaper Claude model and run it. This isn't going to work if it's this slow.")
- **Decision:** Claude Haiku 5.5 is the first narrator, set in `config.toml`, with the API key in `.env`. `start.bat` no longer starts Ollama. The Ollama path through `base_url` stays in the adapter but is not the default. This replaces the "default narrator picked by side-by-side evidence" step of D-020 and makes D-027 optional. If Haiku's prose disappoints, the next step is Claude Sonnet 5.5, a one-line config change.
- **Why:** measured on `qwen3:8b` on the owner's RX 6700 XT: 145 to 359 seconds per turn over 7 turns (`docs/playtests/2026-10-30-local-model.md`), well above what a 20 to 40 minute session can bear. Listed Haiku 5.5 price is $0.10 per million input tokens and $0.50 per million output, and it needs no new adapter.

## D-033 Writing style follows The Primal Hunter, with Path of Ascension and A Soldier's Life

- **Status:** Accepted (2026-10-30; owner's answers in the style workshop forms, https://claude.ai/artifact/5fnPKcTrTudPap9ozbqjTV and https://claude.ai/artifact/3yHuM5FmjjJ7Pee81qzgnc)
- **Decision:** Third person, past tense, plain everyday prose; the character reasons through stats on the page; dry humour; rules explained early through people and the Ledger; some everyday detail; gods with big personalities who talk often; 200 to 400 words, longer for big moments; scenes end on a hook. Prose may use numbers from the sheet or this turn's results, never invented ones (NAR-04 unchanged). 3 to 4 options, tagged with a stat, skill, Oath, class, profession or people the character has, with cost hints kept out of the list (NAR-03 says 3 to 4, as SPEC, the play skill and the validator do; corrected by the design audit 2026-11-06 F22). Oath voices stay oblique and the menu states plain terms. The full sheet, with drawn bars, shows when swearing and on level-up; the real graphic comes with the phone page (M2.5). No book text enters the game or the repo.
- **Deferred by the owner to the next style build:** mid-story Ledger notices with a moment for high-stakes rolls, real odds on options with `/inspect`, and titles. Options show the stat without odds until then. Needs later milestones: first-kill and rift-clear notices (M1, M3.5), skill and item cards (M3.5), exchange-by-exchange fights and post-fight sheets (M1), time skips (M1, G-27), alchemy scenes (M3.5).
- **Why:** the first chat test read as moody and vague, with options that felt like a menu. Samples of book 1 of all three series, read on Amazon on 2026-10-30, use plain explanatory past-tense prose with numbers in the story. The owner asked for options like Baldur's Gate 3: brief, with the stat visible. The Primal Hunter feel was the owner's pick among four samples.
- **Amended by D-052 (2026-11-06):** scenes are 150 to 250 words, longer for big moments. Options outside fights: see D-050.

## D-034 Haiku stays the narrator for every step

- **Status:** Accepted (2026-10-30; owner: blind pick "Y, clearly", then "Better writer for prose, cheap model for the rest")
- **Decision:** Claude Haiku 5.5 runs the referee, prose and scribe steps. This answers D-032's open question for now. The prompt forbids invented belongings and injuries after Haiku's sample did both.
- **Why:** in one blind trial on the same brief and engine roll, the owner clearly preferred the Haiku sample to the Sonnet 5.5 sample. Both ran through subagents, not the game's adapter, so this is one sample and not a measurement. Haiku is about 20 times cheaper per token at list price.

## D-035 Commands stay on screen and need no slash

- **Status:** Accepted (2026-10-30; owner: "the commands are just a little hard to remember")
- **Decision:** Every prompt lists the commands. The whole line `sheet`, `hooks`, `help`, `?` or `quit` works without a slash, while the same word in a sentence stays an action. Oath choices are made by number. Action labels are capped at 12 words.
- **Why:** the owner's first real play of the new style. The opening turn also offered a 16-word option, longer than the brief entries the owner asked for.

## D-036 Options show real odds, and notices land mid-story

- **Status:** Accepted (2026-10-30; owner's approved workshop answers, then "continue" on the recommended order). The two moves below are Assumed.
- **Decision:** A suggested action may carry a check. The engine works out its odds with `check_odds`, the same function the roll uses (GAME-02), and picking the action rolls exactly that check and skips the referee. A stat or skill tag needs a check, and nothing rolls before the Dual Offer is answered, so those tags and checks are stripped until then. Shown chances are limited to 5 to 100 %, because low rolls always succeed. The narrator marks the moment of a result with `<<CHECK>>` and the engine prints the line there; if the marker is missing, the line prints after the prose. `inspect <number>` describes an option without using game time. Assumed: titles move to M1b because no title data exists, and the moment for high-stakes rolls waits for the phone page.
- **Why:** the first live turn tagged a question with `[INTELLECT]` although questions never roll. The owner chose stats and odds on options, dice on every check and notices at the moment they happen.

## D-037 M1b assumptions: Trials, skill evolution and content tables

- **Status:** Assumed (2026-10-30; the owner said to continue with M1b, and canon leaves these open)
- **Decision:** An Ascension Trial is a player's choice, rolled as a Routine check on the class's primary stat against the next tier. Triumph or success is Ascend, success at a cost is Setback (all current XP lost), and failure is Breaking (an Injury of -10 to a random stat, floored at 0). After a Setback or Breaking, a Trial needs a rest first. Ascending levels up, then offers any unlocked evolutions; with none, the class carries on. A rank-5 skill plus a matching shard moves to rank 1 of the next rarity. Offers draw from the `world` random stream. `skills`, `titles` and `evolutions` are optional tables until M3.5's canon batches, so tests use a fixture. Injuries come from Breakings only until pools and overspending arrive (M1d). Curing them waits for Life skills and alchemy. Titles record their check bonus but do not apply it yet, because canon has no list of check kinds. The Hearthwright's Kitcraft fusing rule is transcribed into `classes.yaml` in a `canon:` commit.
- **Why:** `world/power_tiers.md` names the three Trial outcomes without saying which rolls give them. A Setback for a narrow miss and a Breaking for a real failure follow the existing outcome bands.

## D-038 M1c assumptions: forks, save upgrades, calendar, clocks and petitions

- **Status:** Assumed (2026-10-30; the owner said to continue, and M1c is next in the approved plan)
- **Decision:** (1) M1c comes before M1d, following the plan: save upgrades should exist before combat changes the state shape, and nothing here delays combat by much. (2) Schema 2 adds `rng_checkpoint`, one row per stream that moved in a turn, so a fork restores the dice at the end of any turn; a turn costs about 7 KB per moved stream (estimate from 625 state integers). A schema 1 save kept only its latest RNG state, so turns before its first record refuse to fork rather than invent dice. (3) Upgrades run one step per version in one transaction, after copying the save to `<name>.schema<N>.bak`; an earlier copy is never replaced. (4) A fork at turn N ends at turn N's commit. Commands made after it are stamped N + 1 and are redone. (5) The calendar counts minutes from 1 Seedtide 1,140 AS. Spans: minutes up to 240, hours up to 24, rest 8 hours, day 1, days up to 90, with 2 time calls per turn. (6) A season is 90 counted days from the start of play, not a calendar season, because canon says "three in-world months"; Blank Days are not counted. The first segment therefore lands 90 days in, on 1 Longday. (7) A clock's threads count as neglected if no `engage_clock` was recorded in the season just ended. `engage_clock` is a new narrator tool and needs a check that turn, at most once per clock per counted day, because without some way to engage, every clock would always be neglected. The narrator's `advance_clock` waits for M2 with the beats its causes need. A filled clock stops at its segments and its consequence goes to the narrator as due material; no engine effect yet. (8) Clocks hold only moved values, with starts from `world/data/clocks.yaml`, so old saves need no start event. (9) Petitions are hooks with a god and a deadline, from sworn gods only, one open per god. `resolve_petition` is a new narrator tool, not allowed in the turn the petition arrives. First guesses in `world/data/rewards.yaml`: +5 granted, -2 ignored, 7 days. Time lapses an overdue petition as ignored. There is no `petition_sent` event; `hook_registered` carries the fields. (10) `apply_effect` with `rest` now also takes 8 hours, and `advance_time` with `rest` also heals; one rest per turn. (11) Oath timers and daily Boons named in `docs/architecture.md` section 6 are not built: a search of `world/` outside `secret/` and `sealed/` for `Boon`, `timer` and `daily` found no rule to build. (12) Training gives nothing yet (G-27); `advance_time` only moves time. (13) `pantheon fork` and `play --timeline` are built now rather than in M1f, so forks can be used.
- **Why:** canon gives the calendar, segments, rates and the wording of petitions, but not these numbers or how neglect is measured. Each is data or one small rule. With every clock neglected, The Lantern's Price fills after 180 counted days, so the owner's play should decide whether that rate holds.

## D-039 M1d assumptions: exchanges, intents, pools and Reckonings

- **Status:** Assumed (2026-10-30; the owner said to continue, and M1d is next in the approved plan)
- **Decision:** (1) One exchange is one turn. The narrator starts a fight with `start_fight` (1 to 4 foes, at most 2 tiers above the character) and picks the player's `fight_move`: attack, guard or flee. Pure talk runs no exchange. (2) The engine sets each move's difficulty and tier: attack from the target's threat and tier, guard Routine and flee Hard against the highest tier standing. (3) Foes need hits, not hit points, by threat (minion fewest, elite most); a triumph lands more hits than a success, a failure none, and a guarding foe takes 1 fewer. A triumph or success also stops the target's blow. Guard blocks 100 % on success or better, 50 % at a cost, 0 % on failure; flee escapes on anything but failure and blocks the same. (4) Intents are data with weights: a plain strike, a heavy blow and a guarded stance, each dealing a share of maximum HP that shifts with the tier gap, never below the gap step for a foe that deals any. The screen always shows each foe's intent, from the engine. (5) Narrator `apply_effect` damage and resting are refused during a fight, and time passes only in minutes. `end_fight` ends a fight for story reasons, never for the Downed. (6) `fight_move` with a skill replaces `use_skill` for now; skills spend only inside fights. A cooldown of N shuts out the next N exchanges. A skill with no data (an origin's) costs nothing. Overspending must be the player's choice and rolls right after the spend. (7) Downed needs aid (any heal, which also clears marks) or runs out: every turn in a fight while Downed adds a mark whatever the player types. The exchange that drops the character adds none. Outside a fight, Downed adds no marks. (8) A Reckoning heals fully, refills pools and ends the fight. The third also removes one level's fixed stat gains (floored at level 1) and gives an Injury. The second costs no gear yet, because no inventory exists. Shrine locations stay open (G-15), so the narrator only says the character wakes at the last shrine. (9) Permadeath comes from `config.toml`. A dead character's timeline accepts no more turns; forking from an earlier turn still works. (10) Rest now also refills pools and clears cooldowns. (11) An Injury caps wounds at the new maximum HP, so HP never goes negative. (12) Not built: class signature traits (Momentum, Pathsense and the rest), the Turning Tide Oath's HP recovery, the skill-rank form of Injury, and foes with their own intent lists; these come with M3.5's content or the tactics after the first version (D-014).
- **Why:** canon names exchanges, shown intents, pools, marks and the Reckoning ladder, but gives no foe numbers. Counting hits keeps fights to the 1 to 4 exchanges canon asks for, and every number is in `world/data/combat.yaml` for tuning from play.
- **Amended:** by D-045 (nine class traits now run) and D-047 (the second Reckoning and later take carried gear). Every number lives only in `world/data/combat.yaml`. Open: the one measured fight took 5 exchanges and the pacing sim, with fight length from the odds, gives a median of 6 (design audit 2026-11-06 F7, F9); the owner's fight playtest decides whether hits or guard change.

## D-040 AI-Master-Instructions upgraded to v4.4.0

- **Status:** Accepted (2026-11-03; master hooks spec slice S5 roll-out; merged as PR #17)
- **Decision:** `.ai-master.json` pins v4.4.0 (was v0.5.0, D-001), same layers, no overrides, by the master's upgrade checklist. Retired ids repointed: SAFE-03 in AGENTS.md and SAFE-04 in BUILD_PLAN.md to SAFE-01. CI skips draft PRs and runs when one is marked ready (CI-06). The guard hooks are on: nine checks (force push, branch delete, test weaken or delete, secrets, synced-file edits, `pkill -f`) ask the owner before the call runs. New synced skills: write-spec, routing, audit, brainstorm. Not a hooks pilot, so no `docs/harness/drift/`; not node-web, so no test-traps step.
- **Why:** the master rolls every managed project to the hooks release; Pantheon was 17 releases behind.

## D-041 Claude Code is the narrator in session play; saves live on a `saves` branch

- **Status:** Accepted (2026-11-06; owner: "I want it to be something that works on here so I don't have to use API costs", then chose "Yes, build it" for the proposal below)
- **Decision:** `pantheon session` lets the Claude Code session itself act as narrator, paid by the owner's subscription, with no Anthropic API call. Each subcommand is one step of the D-031 turn: `begin` (rolls a chosen option's check and prints the brief), `tool` (referee, then scribe calls, through the same `apply_tool`), `narrate` (the same NAR-04 validators and notice placement), `commit` (one atomic turn). A pending turn is replayed from its recorded calls on every step, so nothing is saved until `commit` (OPS-03). The `/play` skill (`.claude/skills/play/`) holds the narrator's steps. While `data/.playing` exists, the `play-guard` hook keeps secret and sealed canon out of the narrator's context (NAR-02, WLD-04); its rules are D-044 (1) and the hook code. `scripts/saves.sh` stores a text dump of the database as the only file on the `saves` branch, pushed after every committed turn, because cloud containers are wiped. Replies in chat copy the terminal's look. The Pantheon Table page (https://claude.ai/artifact/WoBEwUTajnMQTrPV1NBJ3b, source `docs/play/pantheon-table.html`) shows `session screen`'s JSON from its database and sends a tapped move to this session as a comment sent to Claude; it renders and decides nothing (GAME-02). The Haiku API path (D-032, D-034) stays for `pantheon play`; this replaces it as the default only for play in Claude Code.
- **Assumed:** the guard is weaker than the API path, where the model only ever sees the brief: the narrator session could still open a gated file once play stops. Play on the Windows PC and in the cloud share the `saves` branch; the last push wins, and `pull` backs up a local database it replaces.
- **Why:** play in the cloud session costs nothing per turn beyond the subscription; the engine still owns every number (ENG-01, ENG-02).

## D-042 Twenty-five base classes, halfway to classic fantasy roles

- **Status:** Accepted (2026-11-06; owner: classes "halfway between this and basic pathfinder classes"; on the proposal page https://claude.ai/artifact/96Gk7pos2FRTar4ezcyRfS: cut Wager-bound, add elemental magic, fill wilderness and crafting gaps; then "Change inquest to Inquisitor", a second pass for gaps and look-alikes, "Apply, plus the Seer")
- **Decision:** The roster in `world/data/classes.yaml` and the `world/power_tiers.md` Classes table: Sellsword (was Blade-sworn), Reaver, Warden, Oathknight, Marshal, Fistsworn, Spellblade, Cutpurse, Wayfinder, Inquisitor, Riftwalker, Arcanist, Elementalist, Wildblood, Cantor, Seer, Votary, Hexer, Gravewalker, Wildkin, Greenwarden, Skinchanger, Hearthwright, Runesmith, Gearwright. Each has one signature trait and a one-line blurb. Wager-bound is cut. Arcanist owns the non-elemental schools, Elementalist the elements, Wildblood unstable innate magic; Wayfinder has no animal and Wildkin owns the companion. Each god favours three or four classes (`world/data/gods.yaml`). Names and traits are Caldrenne's own; only the roles echo classic fantasy. New classes and evolutions follow the `class-design` skill.
- **Assumed:** stat pairs were spread so each stat leads four to six classes; five pairs repeat between clearly different roles. The `class-design` skill is a checklist adopted without a cost measurement (DEL-07); review it after its first content batch. Superseded in part by D-045: nine traits run in fights; the other sixteen are canon text until their systems exist.
- **Why:** the owner found the eight classes unclear and narrow; classic roles make a class's feel obvious on the page.

## D-043 AI-Master-Instructions upgraded to v4.11.0

- **Status:** Accepted (2026-11-06; owner: "I would like you to be linked to the AI master instructions", ahead of a full audit)
- **Decision:** `.ai-master.json` pins v4.11.0 (was v4.4.0, D-040), same layers, no overrides. New rules CI-07 (schedule your own CI check after a push) and GIT-08 (finish in the same PR after approval; it supersedes GIT-02, which nothing in this repo overrode). New synced skills `ui-style` and `ui-mockups`; new guard checks `ci.record`, `gate.ci`, `shell.chain`, `edit.noop`, `secrets.read`, and a PostToolUse hook. The `play-guard` hook entry is untouched.
- **Why:** the project was seven releases behind; `sync.mjs --check` from v4.8.0 on notes newer releases so this does not recur silently.

## D-044 Audit 2026-11-06 fixes: the play guard denies by default; the owner's calls taken as recommended

- **Status:** Accepted (2026-11-06; owner: "Ok do what you recommend for all" on `docs/audit/2026-11-06-repo.md` and `docs/audit/2026-11-06-tests.md`)
- **Decision:** (1) The play guard (D-041) runs on every tool (matcher `*`) and refuses any tool it does not name. It allows Bash, Read, Write and Edit as before, `ArtifactData` with files from `data/` only, `ArtifactComments`, and tools that touch no file. Bash is split into shell words. Any operator, redirect, substitution, glob or escape outside single quotes is refused, and so is any `$`, backtick or `\` inside double quotes. The `cd <dir> &&` prefix is gone. `narrate` and `screen` take files under `data/` only. `session export` and `import` run only through `scripts/saves.sh`. Paths are compared after following symlinks, and a call the guard cannot read is refused. (2) M3.5 plans Tier 1 skill lists and evolutions for all 25 base classes (D-042), estimated at about 3 times the work planned for 8. (3) mypy runs strict on all of `src/pantheon` (was `engine/` only, SPEC section 3): the other 25 files needed three type annotations, so the wider scope costs nothing now and stops drift. (4) The canon wording calls (the taught account of Noth, the registrar named Hale) and the open canon questions found by the audit go to `docs/canon_gaps.md` for the owner; no canon text was changed to answer them. (5) The play skill keeps the game page's URL, because the guard does not let the narrator read HANDOFF during play (repo F32 in part). (6) Licences, read from the installed packages' metadata on 2026-11-06: runtime anthropic Apache-2.0, pydantic MIT, PyYAML MIT, rich MIT; dev hypothesis MPL-2.0, mypy MIT, pytest MIT, pytest-cov MIT, ruff MIT, types-PyYAML Apache-2.0. The game pages load Alegreya SC, Spectral and IBM Plex Mono from Google Fonts, which serves them under the SIL Open Font License 1.1 (from memory; not checked from this session).
- **Why:** the audit showed two ways for secret canon to reach the narrator session during play (repo F1, F2): a crafted `cd` prefix, and tools the guard never saw. An allowlist fails closed when a new tool appears.

## D-045 M1d class traits: nine solo fight traits run in the engine

- **Status:** Assumed (2026-11-06; the owner chose "Solo fight traits" for which traits M1d implements; the numbers are the trait text, and how each is read is an assumption)
- **Decision:** Nine of the D-042 traits run in fights, as data in `world/data/combat.yaml` `traits`, keyed by class id. A check bonus adds to the chance after the base formula, shows in the option's odds, and is named on the roll's Ledger line. The numbers below are the canon trait text; the engine reads them only from `combat.yaml`, and `tests/world/test_data.py` checks the two agree.
  1. Momentum (Sellsword): each attack that succeeds (success or better) adds +5 to the next attack, up to +15; a failed or costly attack resets it.
  2. Blood Up (Reaver): while HP is below half (in a fight), attacks get +10 and guard and flee get -10.
  3. Still Centre (Fistsworn): guard and flee roll the best of the named stat, Agility and Resolve; stamina skills cost 20 % less (rounded down). Everyone counts as unarmoured until gear has armour (M1e).
  4. Opening (Cutpurse): when the narrator starts the fight with `ambush: true`, the first attack gets +10 and lands double hits.
  5. Studied Mark (Inquisitor): from the second exchange on, attacks get +10 (one exchange of watching every foe present).
  6. Attuned (Elementalist): a player choice of Flame, Frost, Storm, Stone, Wind or Tide, due once the class is chosen (`choose attunement <element>`). Skills of that affinity cost 20 % less mana and get +5, in and out of fights.
  7. Surge (Wildblood): a move may pay a mana skill's cost in HP, 1 HP per mana, never down to 0.
  8. Malediction (Hexer): once per fight, `trait: true` on an attack curses the target for the fight: +10 on attacks against it and its blows deal 5 percentage points less (foes do not roll, so their -10 becomes the player's +10).
  9. Beast Form (Skinchanger): once per fight, `trait: true` on any move takes the shape for the rest of the fight: +10 on Vigor and Agility checks, and no skills.
  The other sixteen traits stay story text: they need allies (Bulwark, Rally, Sworn Edge's heal), items or crafting (Kitcraft, Rune-Etch, Contraption), skill offers (Spellbook), scenes outside fights (Glimpse, Ancestral Voice, Old Growth, Channel), or spell content (Edgecasting, Carrying Voice, Fold Step, Pathsense).
- **Assumed readings beyond the canon text** (design audit 2026-11-06 F20): Malediction's 5-point cut to the cursed foe's blows has no canon source; Beast Form's "no spells or speech" is read as no skills at all; Studied Mark's "a target" is read as every foe present, and "all checks" as attacks only.
- **Why:** these nine are plain modifiers on the fight's own checks, so they need no new systems; each shows on the move's odds before the player picks it (GAME-04).

## D-046 LitRPG pacing and tone guide M1's remaining build

- **Status:** Accepted (2026-11-06; owner: "keep in mind that this is a litrpg style game / experience and I want that reflected in pacing and tone")
- **Decision:** Engine-side work in M1d to M1f favours what the genre runs on: every gain and loss is a visible Ledger line with its number (trait bonuses on rolls, skill costs, hits, loot drops, coin), progress comes in frequent small steps between the big ones, and fights read exchange by exchange. Reward and loot numbers in M1e are tuned so a session of 20 to 40 minutes shows XP, loot or a level most sessions, inside D-014's Tier 2 pace (about 7 hours since D-047). Prose length (D-033) is unchanged until the owner returns to it.
- **Why:** the owner's direction for the genre; D-033 already names LitRPG models for the prose.

## D-047 M1e rewards: tier-scaled XP, foe XP, loot, coin, items and gear

- **Status:** Accepted (2026-11-06; the owner read the reward page https://claude.ai/artifact/Ry3VXsZ5btuyDTNTYQBoYD, asked for all XP 15 % above the first draft, then chose "Approve", which also moves D-014's Tier 2 target from 8 to about 7 hours). Parts (1), (2) and (8) are the owner's numbers; parts (3) to (7) are build assumptions, marked Assumed.
- **Decision:** (1) Numbers live only in `world/data/rewards.yaml`: narrator XP by kind with a per-turn cap; XP per foe brought down by threat, raised per tier the foe stands above the character and cut per tier below ("very little for those below" in canon is read as 25 % per tier, for the owner to retune), paid by the engine when a fight ends (victory, flight or story end) outside the per-turn cap. (2) All XP and loot coin scale with tier by the canon XP curve divided by 1.5 per tier, so each tier takes about 1.5 times the last (Tier 2 rewards are 2.89 times Tier 1's). (3) Assumed: a won fight searches each fallen foe: one roll on its threat's table, two for an elite; `grant_loot` rolls `cache:<what>` or `bounty:<who>` once a turn, only after a check this turn that did not fail. Tables pay coin, an item or a common affinity fragment, of the place's affinity if the narrator names one, else drawn from the basic fifteen. (4) Assumed: `world/data/items.yaml` holds only the canon price list's items: healing tonic (heals 25 %; in a fight it is the whole exchange, with no roll), dagger (+5 on attacks), sword (+10), chain shirt (each blow 5 points of HP percent softer; Still Centre needs no armour), rope. (5) Assumed: `adjust_inventory` hands over common or uncommon items of the character's tier, at most 3 a turn; `adjust_currency` pays or charges coin, never overdrawn, at most 30 sp gained a turn at Tier 1. Coin is kept as silver plus 0 to 11 copper. (6) Assumed: the player equips a weapon and armour outside fights and uses consumables (`session use`, `equip`, `unequip`). (7) Assumed: the second Reckoning and later take carried gear and keep what is equipped (canon), replacing D-039 (8)'s "no gear yet". (8) `scripts/pacing_sim.py` estimated 7.0 hours to the Tier 2 Trial at an assumed 20 turns an hour with every fight 3 exchanges long. After the design audit (F8 to F10) it takes fight length from the odds and counts shards per affinity: 9.9 hours (middle half 9.2 to 10.7), excluding Trial retries, with a median fight of 6 exchanges and the first fusable shard in session 16.7 (estimates; run 2026-11-06, seed 1). D-014's target stays about 7 hours; whether to retune waits for the owner's fight playtest. Its play pattern is an estimate for playtests to replace.
- **Why:** canon says XP comes from foes, rifts, bounties and milestones and scales with tier, and names prices, but gives no amounts (G-08). The owner wanted LitRPG pacing (D-046) and a slightly faster climb.

## D-048 A due thread always gets one way back

- **Status:** Accepted (2026-11-06; owner: "Go with your recommendation for the hook option change to keep me back on track")
- **Decision:** When the due material lists a due hook, or a clock that has moved or filled, one of the 3 to 4 suggested actions leads toward that thread in the scene's own terms, and the closing weighing of choices names it. It is one action per turn, only while something is due, and the player may ignore it. This is a narrator-prompt rule (`prompts/narrator.md`, Choice design), so it relies on the narrator; M4's beat scheduler and engine-evaluated due hooks are where the engine enforces it.
- **Why:** options grow from the current scene, so picking a side path made every next menu about that side path, and nothing pulled the player back to open threads. The owner noticed this in past play.

## D-049 Design audit 2026-11-06: findings accepted; the owner's calls taken as recommended

- **Status:** Accepted (2026-11-06; owner: "Do as you recommend" on `docs/audit/2026-11-06-design.md`)
- **Decision:** (1) NAR-06 and NAR-07 apply to session play as well as `pantheon play`: rejections are capped and dropped calls recorded (F4); built in M2. (2) Fight length is a tuning item for the owner's fight playtest; D-039's hits and guard rule stay until then (F7). (3) D-039 and D-045 become Accepted, or list changes, after that playtest (F19). (4) Three trait readings are named as Assumed under D-045 (F20). (5) Combat gets ENG-12 and class traits ENG-13 in SPEC; their tests carry the IDs (F5). (6) Numbers live in data files only, with tests where canon text repeats them: `combat.yaml` against the trait text, `items.yaml` against `world/economy.md` (F13, F16). (7) Whether options stay is settled first in the M2 planning interview, as its own entry (F3).
- **Why:** the audit found the M2 plan and architecture out of date, several facts in more than one home, and canon questions with no gap entry.

## D-050 Odds without an option menu: odds in the closing thought, and a preview for typed actions

- **Status:** Accepted (2026-11-06; owner, on the mock-up https://claude.ai/artifact/8jXbpgTg7zXjRk7bhfWZxb: "let's go with c for now and potentially switch to a in the future"). Settles design audit F3 (the audit named it D-049; PR #24 took that number).
- **Decision:** In session play outside a fight, there is no numbered option menu.
  - The scene's closing thought marks the approaches the character weighs with `<<ODDS n>>`, and at commit the engine prints each one's odds there, such as "(Agility 38%)" or "(no roll)". The odds come from `check_preview`, the same calculation as the roll (D-036).
  - A typed action that needs a roll is previewed first (`Preview: Agility check, hard: 38%`). `session go` rolls exactly that check; `session abandon` backs off with nothing rolled. Within a turn, a stat's first preview fixes its difficulty and tier, so rewording the same approach cannot reshop the odds; a different stat gets its own.
  - A suggested action whose odds the last scene did not print is previewed when picked, so nothing rolls at odds the player did not see.
  - `suggest_actions` is still required (NAR-03). It is now the engine's record of the approaches, not a menu. D-048's way back is one of the approaches the closing thought names.
  - Fights keep their numbered moves beside the foes' intents (D-039).
  - The API path (`pantheon play`) keeps its menu for now.
  - The game page shows a Go and Back off card for a preview, and no option list outside a fight.
- **Assumed:** prose may be replaced before commit (`narrate` again), so a wrong marker can be fixed. A preview costs one extra step on risky typed actions only.
- **Why:** the owner likes seeing the odds before acting, but found the option menu kept them on the listed paths. Shape A (preview only, no odds in the prose) stays the likely next step, if the closing thought still pulls too hard toward its listed approaches.
- **Amended by D-051 (2026-11-06):** only Hard checks or harder stop at the preview; Routine checks roll at once. From M2b, `pantheon play` gets this design too (D-052).

## D-051 Only Hard checks or harder stop at the preview

- **Status:** Accepted (2026-11-06; owner's M2 round 1 answers, https://claude.ai/artifact/S1M8kTeHdi6pX1njM7FXvA, the review, https://claude.ai/artifact/LcHA2Zu4vbVaX4jYuhdBEP: "Go with recommendations and I approve", then in chat: keep PR #25's design and add this threshold). Amends D-050.
- **Decision:** (1) D-050 stays: no menu outside fights, the closing thought prints each approach's odds, and fights keep their numbered moves. (2) A typed or picked action stops at the preview only when its check is Hard, Severe or Heroic. A Routine check rolls at once, and its notice shows the chance and the roll, as D-036's notices do. (3) D-050's rule that a stat's first preview fixes its difficulty and tier for the turn stays the guard against rewording. (4) If the closing thought still pulls the owner toward its listed approaches after the M2a playtest, the next steps on the table are D-050's shape A or 2 to 3 tap-to-fill hints with no odds (the owner's round 1 answer, given on a form that wrongly said tapped options were still in place).
- **Why:** the owner said "I was thinking too much about optimizing choices" and wants play to feel "like a narrated litrpg book / game / choose your own adventure". Fewer pauses mean fewer numbers to weigh. Both reviews found that a pause on every roll invites fishing for odds.

## D-052 M2 is the remaining narrator work, built in four parts

- **Status:** Accepted (2026-11-06; same approval as D-051). Settles design audit F1.
- **Decision:** (1) **M2a The feel:** D-051's preview threshold; scenes of 150 to 250 words, longer for big moments (amends D-033), with the number in one home (it is in both `prompts/narrator.md` and `narrator/assemble.py`, SRC-01); NAR-03 and NAR-08 in SPEC to match D-050 and D-051. The owner then plays a session with a fight. (2) **M2b Reliability:** NAR-06 and NAR-07 in session play (D-049 (1)): rejections counted in the pending turn, at most 2 retries, a dropped-call event at commit, and a fallback turn that commits without new suggestions. `pantheon play` gets D-050's design through the same engine function. A scripted 10-turn run on both paths. (3) **M2c Story tools:** `introduce_npc`, `introduce_location`, `offer_oath` (the player still accepts by command, D-029), `test_burden`, and `advance_clock` with each clock's allowed causes as data (a `canon:` round). (4) **M2d Bounty board:** 3 to 5 Tallyhouse bounties as data (a `canon:` round), and `record_beat` for their beats with a minimal schema M4 may extend. M3.5 batch 4 adds more bounties. (5) **Cut:** the Ollama side-by-side (D-032 settled it), streaming prose (D-029: NAR-04 must see the whole reply), gear commands on `pantheon play`, and the cost-estimate step (SAFE-01 still asks for an estimate before any paid Haiku playtest). Also cut: `begin_trial` and `resolve_trial`, since `session trial` runs the Trial as the player's choice (D-037). (6) **Later:** `grant_title` in M3.5 with titles data; `resolve_oath_conflict` becomes a player command once canon defines Oath conflicts. (7) Pacing stays as D-047 (8) until the owner's fight playtest. (8) **Acceptance:** the scripted run on both paths with NAR-04, NAR-06 and NAR-07 checked, plus the owner's played sessions; the owner's call is the measure (GAME-06).
- **Why:** M1.5 to M1.7 and PR #25 built most of the old M2 list. The kept remainder is about 4 to 6 sessions (estimate), so the part the owner feels comes first and is played before the rest is built.
- **Amended (2026-11-06; owner: "Let's wait on play test until after m2 is complete"):** the owner's playtest with a fight moves from after M2a to after M2d. M2a merges without it.

## D-053 M2b assumptions: retries, the session fallback and odds on `pantheon play`

- **Status:** Assumed (2026-11-06; built from D-052 (2), spec `docs/specs/m2b-reliability.md`)
- **Decision:** (1) NAR-06's "at most 2 retries" is 3 tries a turn for each tool and for the prose, on both paths (`config.max_tool_retries`); the third rejection drops the tool and commit records one `tool_call_dropped` event. `narrator/loop.py` now tries the third call instead of skipping it. A call to a tool not offered at that step is refused without counting. (2) In session play the fallback turn (NAR-07) comes only from three rejected narrations; it keeps every accepted event and the previous suggestions. A dropped `suggest_actions` commits the turn with none, so in a fight the player types the move. (3) `pantheon play` follows D-050 and D-051: no list outside a fight, a bare number there is refused, `inspect` works on fight moves only, the Dual Offer is numbered from 1 outside fights, a Hard or harder check stops at "Go ahead? (y/n)", and the closing thought's markers are stamped from `engine/preview.py`, the one module both paths use. An out-of-range marker is removed there and refused in session play. (4) `pantheon play` keeps a turn's stat locks in memory; quitting mid-turn saves nothing and drops them. (5) `prompts/narrator.md` is the one home of the closing-thought marker rule.
- **Why:** D-052 (2) names the behaviour but not these edges; each choice matches the existing API loop or D-050 where one exists.
