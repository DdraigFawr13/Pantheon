# Audit: whole repository before M0 (2026-10-30, second pass)

Scope: every tracked file at `90e2629` (main after PR #4), plus the open draft PR #5 (D-019, D-020). The first audit (`docs/audit/2026-10-30-pre-m0.md`) covered the design at `b3a519b`; all of its applied items were checked and are in place. This pass covers what changed since (PRs #2 to #5), the process files (`.claude/`, CI, hooks, config, `.gitignore`, `scripts/`), the world canon as a set, and the plan itself.

Method: read in full every file under `docs/`, `prompts/`, `scripts/`, `.github/`, `.claude/settings.json`, `.claude/hooks/`, `.claude/agents/`, `.ai-master.*`, `.gitignore`, `.env.example`, `config.example.toml`; grepped `world/power_tiers.md` and `world/protagonist_seed.md` for the rules SPEC encodes; delegated a read of all of `world/` (public, secret and sealed) to a reviewer agent under the WLD-04 rule (sealed and secret files are named here only by file name and frontmatter key); ran `node .claude/master/sync.mjs --check` (OK), `scripts/render_plan.py` (renders), `git check-ignore` on the planned `world/data/` path, and fetched the Ollama compatibility page that D-020 cites. Assumed load: one owner, one local process, SQLite, two Claude sessions working on the repo at the same time (PR #5 and this branch).

Ranked by the rework they cause if left. Each item names the case that goes wrong and the smallest fix.

## A. Breaks M0 as planned

1. **`.gitignore:3` `data/` also ignores `world/data/` and `world/sealed/data/`.** The pattern has no leading slash, so it matches a `data` directory at any depth. Checked: `git check-ignore -v world/data/affinities.yaml` reports `.gitignore:3:data/`. Case: M0 step 9 ("first `world/data/` tables") writes the canon YAML, `git add` skips it, CI passes on a tree without it, and the loader test passes locally only. Fix: change line 3 to `/data/`.

2. **`world/sealed/README.md` has no frontmatter, but roadmap M0 says the loader "parses every file in `world/`" and the acceptance is "all world files load".** Case: the loader either fails M0 acceptance on this file or needs an undocumented exception. Fix: write the rule once in SPEC WLD-01: the loader reads `world/**/*.md` except files named `README.md`, and a test asserts the README is not in the lore index (it must never reach a prompt).

3. **Reveal gates depend on six flags that nothing defines or sets.** Gates in `world/secret/` and `world/sealed/` reference `flags.met_drovash_vessel`, `flags.prophecy_bought`, `flags.rifts_closed`, `flags.unwritten_path`, `flags.sealed_a_trace_ready`, `flags.sealed_a_trace_seen` (grep of `flags\.[a-z_]+` over `world/`, `prompts/`, `docs/`). Only the last three are named anywhere else (D-012). `set_flag` says "Namespaced keys only" (`docs/architecture.md:138`) but no namespace list exists, and the event list (`docs/architecture.md:118`) has no rift lifecycle event (`rift_entered`, `rift_floor_cleared`, `rift_closed`) although `rifts_closed` drives five of the eight gates. Case: the narrator never calls `set_flag("prophecy_bought")` because no prompt or data file names it, so the Ilvane foreshadow can never release; or it sets `prophecy_bought` to 99 in one call. Fix: a `world/data/flags.yaml` registry (`key`, `type`, `owner: engine | beat | narrator`), counters owned by the engine only, a `rift_closed` event that increments `rifts_closed`, and the M0 "every gate parses" test extended to "every path in a gate resolves to a registered flag or state field". This is the WLD-04 reachability test, applied to secret gates too.

## B. One fact, two homes (SRC-01)

4. **Two package layouts.** `docs/SPEC.md:74-85` lacks `storage/`, `sealed/` and `config.py` and labels `ui/web/` "M5 interface"; `docs/BUILD_PLAN.md:54-70` has them and the roadmap builds the web page at M2.5. The import-boundary test and the mypy path are specified from SPEC. Fix: SPEC section 4 keeps the boundary rule and points to the BUILD_PLAN layout; delete the SPEC tree.

5. **The build plan is "Proposed" but the handoff says to execute it.** `docs/BUILD_PLAN.md:3` says "Status: Proposed" and "(D-001 to D-017)"; `docs/HANDOFF.md:7` says "Next: M0 per `docs/BUILD_PLAN.md`"; no DECISIONS entry approves the plan (SRC-04). PR #5 edits the plan without changing the status. Fix: the owner says "approved" once; the status becomes Accepted with the date and the range becomes "D-001 onward".

6. **`docs/KICKOFF_PROMPT.md` is stale and duplicates AGENTS.md.** Its read order omits LESSONS and BUILD_PLAN (`:6` versus `AGENTS.md` "Read first"), it tells the session to "continue into M1 without waiting for approval" (`:8`) although M0 ends with a canon batch the owner approves, and lines 10 to 15 restate rules that live in AGENTS.md. Case: a fresh session pasted this prompt skips LESSONS and the plan. Fix: cut it to "Read AGENTS.md and follow it. Execute the next step in docs/HANDOFF.md."

7. **PR #5 names a config key that the example file does not have.** The plan text in PR #5 says the Ollama switch is "`base_url` in `config.toml`", but `config.example.toml` is not in the PR's diff. Fix in PR #5: add `base_url = ""` under `[models]` with a comment, and `ANTHROPIC_BASE_URL` is not needed because the adapter reads config (OPS-02). The D-020 claims themselves are correct: the Ollama page lists Messages API, streaming, system prompts and tools as supported, and `count_tokens`, `tool_choice`, `cache_control` prompt caching and `metadata` as not supported.

## C. Design gaps to close before the event schema freezes (M1) or the loop is built (M2)

8. **Two paths in the turn loop record prose that skipped NAR-04.** `docs/architecture.md:59-62`: after two failed prose validations the loop `break`s and records the third reply unchecked; `:75`: the forced-prose round (`tools=None`) is never validated. Case: the model writes "you take 12 damage" in the forced round and the number enters the chronicle. Fix: validate every reply that will be recorded; when the cap is reached, use the NAR-07 fallback renderer (already specified) instead of the invalid prose.

9. **`advance_clock` asks the engine to judge narrative eligibility.** `docs/architecture.md:140`: "Rejects if clock is not narratively eligible" is not computable. Case: the narrator advances the Rift Tide two segments every turn and nothing stops it. D-014 already fixes the clock rule (one segment per season, one more when neglected) and roadmap M4 advances clocks "on elapsed in-world time and on events". Fix: delete the tool; clocks move only from `time_advanced` and from engine events.

10. **A Breach is decided by the model with no visible step.** `test_burden` (`docs/architecture.md:134`) applies a suspended blessing and -20 Standing on the narrator's `kept: false`. This follows D-010, but GAME-04 wants consequences visible. Case: the model misreads a scene, the player loses a blessing and never learns why. Fix: the `burden_tested` event carries the narrator's `situation` and the status panel and `pantheon log` show it; no rule change.

11. **`visibility` has no `sealed` value.** WLD-01 allows `public` or `secret`; both sealed files declare `visibility: secret` and `type: sealed-lore`. The stricter WLD-04 handling is keyed only on the folder path. Case: a sealed file moved into `world/secret/` by mistake loses sealed handling and no test fails. Fix: add `sealed` to the enum and have the loader assert `visibility: sealed` if and only if the path is under `world/sealed/`.

12. **`scripts/render_plan.py:129` stamps the HEAD commit even when the plan files are uncommitted.** The live plan artifact says "at 90e2629" but shows PR #5's D-019 rows, which are not in `90e2629`. Case: the owner compares the page with `main` and the text differs. Fix: append `+uncommitted` when `git status --porcelain docs/BUILD_PLAN.md docs/roadmap.md` is non-empty.

## D. Process and hygiene

13. **Every PR so far (#1 to #5) was opened from the same branch name** `ccr-7b10b8f3-92eyt1`. GIT-01 says never reuse a merged branch. The cloud harness assigns the name and the branch is re-cut from `main` each time, so the history is clean, but the prune workflow deletes it at every merge and a stale local clone can push old history to it. Fix: record the harness constraint as an override of GIT-01 in `AGENTS.md` "Overrides" and `.ai-master.json`, or ask for a new branch name per session.

14. **Two sessions edit `docs/HANDOFF.md` at once.** PR #5 changes "Next", "Open questions" and "Decisions since"; this branch adds one "Just done" line. Fix: merge PR #5 first; the audit PR then rebases.

15. **CI skips docs-only changes with `paths-ignore`** (`.github/workflows/ci.yml:7`). If the `check` status is ever made required in branch protection, a docs-only PR cannot merge because no run reports a status. Not a defect today (D-003). Note for the moment branch protection is turned on.

16. **`docs/LESSONS.md` has no entries after four merged PRs and one redone design round** (D-007 names "two superseded final pages"). No specific mistake is asserted here; SRC-05 asks for one line per mistake found, so the redo is the likely first entry.

17. Small: `docs/DECISIONS.md` lists D-017 before D-016; `docs/architecture.md:91-92` budgets 11,500 tokens for layers 1 and 2 while `:100` estimates 4,300 from the files on disk (keep one number); `.claude/settings.json` allowlist is read-only commands only, which is right.

## E. Canon (from the reviewer agent's read of `world/`)

Frontmatter is consistent: all 15 lore files use `id`, `type`, `visibility`, `tags`, and the secret and sealed files add `reveal_gate`; every block is well formed and every id is unique. No public file or the narrator prompt states a hidden fact. Items 18 to 20 were re-read in the main session; items marked "reviewer" are the agent's report, not re-read here (REP-04).

18. **Do the Unwritten have a Ledger?** `world/protagonist_seed.md:56` ends the opening with "a Ledger open in the mind for the first time", but the player may refuse both Oaths (`:50`), and `world/00_overview.md:20` says "Anyone who swears an Oath gains the **Ledger**". Case: the narrator shows an Unwritten player a status screen canon says they do not have, or the engine hides the status panel from them. Fix: one canon line on the Unwritten and the Ledger; make `:56` conditional.

19. **Nine Sovereigns and three Heirs exist in the tier table and nowhere else.** `world/power_tiers.md:57-58` counts them; no faction, place or god file names a Tier 6 or 7 person (grep `Tier (6|7)|Sovereign|Heir` over `world/`: only the council office at `factions.md:17,82` and `pantheon.md:22`). If they are meant to be hidden, say so in `canon_gaps.md`; `introduce_npc` needs to know whether the narrator may invent one.

20. **Sea travel is 1,000 km per day** (`world/00_overview.md:33`) on a continent 2,400 km wide (`world/geography.md:10`), against 25 and 50 km per day on land. Likely a typo for 100. Case: `advance_time` for a voyage gives absurd durations.

21. **Starting stats exceed the Tier 0 range.** The array 30, 27, 24, 20, 18 plus +3 and +2 (`world/protagonist_seed.md:17`) reaches 35; the Tier 0 typical range is 15 to 30 (`world/power_tiers.md:51`). Minor: `par(0) = 20` still makes the maths fair, but the table misdescribes the player.

22. **Two wordings for the same Oath perks.** `world/protagonist_seed.md:45-46` ("will always be able to tell when others lie"; "reroll a failed check each day") versus `world/power_tiers.md:128,133` ("Sense a knowing falsehood in spoken words"; "Reroll one failed check per day"). The engine's `oaths.yaml` must pick one; the narrator reads both. Fix: the seed quotes the table.

23. **Names.** "The Tallyhouse of Brannock" (`world/geography.md:33`) and "Brannock Tallyhouse" (`:50`). Reviewer: Houses, Harbor-Houses and Seven Houses are used for the same bodies across `factions.md` and `geography.md`. FTS5 retrieval keys on names (MEM-03), so one spelling each.

24. **Gaps missing from `docs/canon_gaps.md`.** Verified: the cults "the Ironwrit" and "the Turning" (`world/pantheon.md:39,47`) are defined nowhere (grep over `world/`). Reviewer: no list of mundane skills although the seed grants Lore, Streetwise and Ritual; no taxonomy of check categories ("Wilds checks", "stealth in the wild"); no rules for "rest" and "the last shrine" although both drive pool refill and respawn; the Unwritten take professions "at awakening" but never awaken; the Sunken Stair has no affinity; "a Rare or better Life skill" (`world/power_tiers.md:73`) is undefined. Fix: add G-10 onward; the owner answers them when M3.5 content needs them.

25. **`docs/canon_gaps.md` breaks its own format.** Line 3 requires RESOLVED entries to cite the commit; none does. The `path:line` references for G-01 to G-05 point at lines rewritten by PR #2. Fix: short hashes; drop line numbers from resolved entries.

26. **Loader decisions the canon leaves open.** `type` has no closed vocabulary (eleven values in use: `setting`, `factions`, `places`, `peoples`, `character-creation`, `rules`, `economy`, `gods`, `secret-core`, `secret-foreshadow`, `sealed-lore`), and ids follow three conventions (`overview`, `secret_the_seat`, `sealed_a_trace`). Fix: list the types in the Pydantic schema and state that ids are free-form but unique.

27. **A pointer to the secret folder sits in the canon prefix.** `world/pantheon.md:65` "See `world/secret/` if released." tells the narrator a secret exists on every turn. The loader handles release (NAR-02). Fix: delete the pointer in the next `canon:` batch.

28. **Stale terminology in a secret file.** `world/secret/the_seat.md` still uses one mechanic term that D-008 removed from the public rules (one hit by count; the term is not named here). Fix in the next canon pass, as a `canon:` commit the owner approves by file name.

29. **Sealed files, by structure only.** Both have the five keys, neutral ids and the three D-012 flags declared. `world/sealed/README.md` names "the content limits" without linking D-016 and gives the gate rules without linking architecture section 7. One outline-level question for the sealed reviewer: D-012 says the affinity is "not takeable in the first version", but `sealed_a.md` has "Who can use it" and "Skills (initial list)" sections and its gate can open from Tier 2 or the Unwritten path. The first-version lock should be a flag the engine does not set before the content exists, not the gate.

## F. Thoughts on the plan

- **Narrated play arrives late.** The plan builds 26 tools, about 50 event types and 17 engine modules before the first live turn (M2, sessions 6 to 11 of 13 to 18). Its own risk list puts narrator obedience and balance first, and both are tested last. Proposal (WS-02, owner's call): after M1a (dice) and a thin M1c (events, fold, snapshot), build a thin M2 with six tools (`request_check`, `apply_effect`, `grant_xp`, `set_flag`, `register_hook`, `suggest_actions`) and play the opening scene against `MockClient` and one live model by about session 5. The remaining M1 systems then land behind the same tool and event pattern. The determinism and replay tests do not get weaker; they get a real transcript to replay.
- **D-020 (Ollama) is sound as written** and the M2 side-by-side test is the right gate. Expect tool-call compliance on 8B models to decide it, not prose quality. Without `tool_choice` the forced-prose round still works (send no tools). Without `count_tokens` the MEM-04 budget is an estimate; log the provider's reported usage after each turn and correct the estimator from it.
- **The sealed-canon process has one soft spot.** The reviewer agent reads sealed text and its report comes back to the main session, which the owner reads. Protection rests on the brief. Fix: a fixed brief in `docs/sealed_review.md` (name files and headings only, never quote the body) that every sealed review cites, and WLD-04 points to it.
- **Dependencies.** PyYAML, anthropic, uvicorn and jinja2 are the standard choices; D-019 records them with licences. Nothing in the stack needs a paid service beyond model usage.

## Not checked

Lore prose for story quality; `.claude/master/sync.mjs` and the synced skills (they pass the drift check and are owned by AI-Master-Instructions); the sealed files' body text against the D-012 outline (the reviewer agent reported on structure only); GitHub branch-protection settings (no API access from this session); the Ollama tool-call quality claim in D-020 (no local model here).

## Debt ledger

`git grep -nE '(#|//|/[*]|--|<!--) ?shortcut:'` over the tree: No shortcut debt.
