# M2b Reliability

- **Status:** Shipped 2026-11-06 (PR #28; assumptions accepted as D-053)
- **Planned in:** M2 round 1 (https://claude.ai/artifact/S1M8kTeHdi6pX1njM7FXvA), review and round 2 (https://claude.ai/artifact/LcHA2Zu4vbVaX4jYuhdBEP), approved in chat 2026-11-06. **Decisions:** D-049 (1), D-050, D-051, D-052 (2), D-053 (this slice's assumptions).

## Problem

From the design audit (F4, `docs/audit/2026-11-06-design.md`) and D-052: session play, where Claude Code narrates, has no cap on rejected tool calls and no fallback. `session tool` prints "Rejected" and keeps no count (`src/pantheon/ui/cli/session.py`, `tool`), and `session commit` refuses a turn with no suggestions (`commit`), so a narrator that keeps making a bad call can stall a turn for ever. `pantheon play` (the API path) caps and falls back, but still shows the numbered option menu that D-050 removed from session play, and rolls a Hard check without showing its odds first (NAR-08).

## Goals

- Both paths, one rule: each tool, and the prose, gets a first try and 2 retries a turn (`config.max_tool_retries`). The third rejection of a tool drops it for the rest of the turn and records one `tool_call_dropped` event at commit (NAR-06). `narrator/loop.py` changes to match: today it skips the third call instead of trying it.
- Session play: after 3 rejected narrations, `session commit` commits a fallback turn with engine text and `is_fallback = 1`, keeping the previous suggestions (NAR-07).
- Session play: when `suggest_actions` was dropped, `session commit` commits the turn with no suggestions instead of refusing (D-052 (2)).
- `pantheon play`: no option menu outside a fight; the closing thought's `<<ODDS n>>` markers become "(Agility 38%)" or "(no roll)"; a Hard, Severe or Heroic check stops at a preview and rolls only on the player's yes (D-050, D-051, NAR-08).
- Both paths get the preview rule, the stat lock and the odds stamping from one engine module, `src/pantheon/engine/preview.py`.
- A scripted 10-turn run on each path passes, checking NAR-04, NAR-06 and NAR-07.

## Non-goals

- Gear commands on `pantheon play` (cut, D-052 (5)). Streaming prose (D-029). The Ollama comparison (D-032).
- No change to fights: they keep numbered moves beside the foes' intents (D-039), and fight moves never preview.
- No new tools (M2c) and no bounty data (M2d).
- No change to the game page: it already shows no option list outside a fight and a Go and Back off card.
- No live Haiku run (SAFE-01 asks for a cost estimate first; the owner plays after M2d).

## Journeys and checks

### J1 Session play drops a tool that keeps failing

- **Given** a turn with accepted prose
- **Given** a turn whose Hard climb rolled (so `grant_xp` is offered) and whose prose is accepted
- **When** the narrator sends `grant_xp` with a bad `kind` three times, then a valid one
- **Then** the replies read "Rejected (2 retries left)", "Rejected (1 retry left)", then "grant_xp is dropped for this turn"; the valid call is not applied; `session commit` saves one `tool_call_dropped` event with `tool: grant_xp`, and XP stays 0. **Check:** `test_nar06_session_drops_a_tool_after_its_two_retries`

### J2 Session play commits without new suggestions when `suggest_actions` is dropped

- **Given** accepted prose ending with an `<<ODDS 3>>` marker, and `suggest_actions` rejected three times (an empty list)
- **When** the narrator runs `session commit`
- **Then** the turn commits, `state.suggested` is empty, a `tool_call_dropped` event names `suggest_actions`, and any `<<ODDS n>>` marker is removed from the saved prose. **Check:** `test_nar06_session_commits_without_suggestions_when_suggest_actions_is_dropped`

### J3 Session play falls back after three rejected narrations

- **Given** a turn whose prose is rejected 3 times (each with a number the engine did not return)
- **When** the narrator runs `session commit`
- **Then** the turn commits the text from `narrator/fallback.render` with `is_fallback = 1`, every accepted event of the turn is kept (the rolled check among them), the previous suggestions stay, and no rejected prose is saved. After the first and second rejections `commit` refuses. A fourth `narrate` that passes replaces the fallback with normal prose. **Check:** `test_nar07_session_commits_a_fallback_turn_after_three_rejected_narrations`

### J4 `pantheon play` previews a Hard check

- **Given** a sworn character in `pantheon play` with `MockClient`
- **When** the player types an action and the referee calls `request_check` at `hard`
- **Then** the screen shows "Preview: Agility check, hard: N%" and asks "Go ahead? (y/n)"; before the answer no `check_resolved` event exists and the turn count is unchanged; on "y" exactly that check rolls (same stat, difficulty and tier in its event) and the referee is not called again; on "n" no turn is saved and the player is asked again. **Check:** `test_nar08_play_previews_a_hard_check_and_rolls_it_on_yes`, `test_nar08_play_backing_off_saves_nothing`

### J5 `pantheon play` rolls a Routine check at once

- **Given** the same setup
- **When** the referee calls `request_check` at `routine`
- **Then** it rolls with no question (no "Go ahead?" is asked), and its ledger line shows the chance and the roll (D-051). This part already holds today; the check guards it against the gate. **Check:** `test_nar08_play_rolls_a_routine_check_at_once`

### J6 `pantheon play` shows odds in the closing thought, not a menu

- **Given** a turn whose prose ends "He could climb <<ODDS 3>>, or ask <<ODDS 1>>." and whose `suggest_actions` has a check on action 3
- **When** the turn commits
- **Then** the saved narration reads "(Agility N%)" and "(no roll)" in place of the markers, N from `check_preview`; outside a fight no numbered option list is printed, a bare number is answered "There is no list outside a fight; type what you do.", and `inspect` says it works on fight moves only; the Dual Offer is numbered from 1. Inside a fight the numbered moves still print (already true; kept as a guard). **Check:** `test_d050_play_stamps_closing_thought_odds_and_shows_no_menu`, `test_d050_play_numbers_the_dual_offer_from_one`

### J7 A rewording cannot reshop the odds on `pantheon play`

- **Given** the player backed off a Hard Agility preview this turn
- **When** they type a reworded action and the referee asks Agility at `routine`
- **Then** the preview shows the first difficulty and tier again and waits. **Check:** `test_nar08_play_locks_a_stats_first_preview_for_the_turn`

### J8 Ten scripted turns on each path

- **Given** a new character, a scripted narrator and scripted player input
- **When** 10 turns run, covering a Routine roll, a Hard preview taken, one backed off, a tool dropped after its retries, prose rejected once for a stray number, a fallback turn and closing-thought odds. The play run scripts `MockClient` replies and the player's `ask` lines through `main(["play", ...])`; the session run drives `main(["session", ...])` with the `Game` helper imported from `tests/test_session.py`.
- **Then** 10 turns are saved; every number in each saved narration is in that turn's event payloads or the sheet (`numbers_in`), so none was invented (NAR-04); the dropped tool has its event (NAR-06); the fallback turn has `is_fallback = 1` (NAR-07). **Check:** `test_m2b_scripted_ten_turns_on_pantheon_play`, `test_m2b_scripted_ten_turns_in_session_play`. The older `test_nar_ten_turn_scripted_playtest_commits_and_replays` (`tests/narrator/test_loop.py`) calls `take_turn` directly and covers neither the CLI nor the preview.

## Decisions

- NAR-06 and NAR-07 apply to session play (D-049 (1)).
- No option menu outside fights, closing-thought odds, a preview for typed actions (D-050), only Hard or harder previews (D-051), on both paths from M2b (D-052 (2)).
- Assumed (D-053): "at most 2 retries" means 3 tries; the third rejection drops the tool. Counted per tool name; a call to a tool that is not offered now, or with JSON that does not parse for one that is not offered, is refused without counting (it changes nothing, and the step text names what is offered).
- Assumed (D-053): the session fallback is reached only by rejected prose, since a Claude Code narrator cannot be "unavailable" mid-turn; `session abandon` stays the way out of anything else. A dropped `suggest_actions` in a fight leaves no numbered moves; the player types the move, which the fight referee rolls (D-052 (2) asks for a turn without new suggestions).
- Assumed (D-053): `pantheon play` takes free text outside a fight; typing a bare number there no longer picks a suggested action (there is no menu to number). The Dual Offer's numbered choices stay, numbered from 1.
- Assumed (D-053): on `pantheon play` an `<<ODDS n>>` marker with no matching action is removed and noted in `TurnOutcome.log`; in session play it is still refused at commit so the narrator can fix it, except when `suggest_actions` was dropped, when all markers are removed (with the space before each).
- Assumed (D-053): `pantheon play` keeps the turn's stat locks in memory; quitting mid-turn saves nothing and drops them. The phone page (M2.5) replaces this UI.
- Assumed (D-053): `prompts/narrator.md` becomes the one home of the closing-thought marker rule; the play skill points to it (SRC-01).

## Alternatives rejected

- **Keep D-050's logic in `Session` and copy it into `Game`**: two homes for one rule (SRC-01, GAME-02); they would drift the first time the threshold changes.
- **Have the API referee re-run after the player says yes**: one more paid call per preview, and the model could propose a different check than the one previewed. The previewed check is passed back as `chosen_check`, which skips the referee.
- **A `session fallback` command the narrator can call at will**: lets the narrator skip a hard scene by giving up. Tying the fallback to 3 rejected narrations matches the API path.
- **Count rejections in a side file (like `previews.json`)**: the count belongs to the turn and dies with it; `Pending` already holds the turn's inputs and is dropped by `abandon`.

## Risks

- `test_play.py` drives picks by number outside fights → those tests change to typed text; any test that only checked the menu is replaced by J6's check, never deleted without a replacement (VER-01).
- A rejected-count keyed by tool name lets one bad `grant_xp` block a later good one → same as the API path (D-053); `abandon` restarts the turn.
- Moving the odds stamping into the engine puts a text marker in engine code → the module only replaces `<<ODDS n>>` with engine numbers and imports nothing from `narrator` (the import-boundary test still guards it).

## Design

**`src/pantheon/engine/preview.py`** (new; engine only). Moves out of `ui/cli/session.py`:

- `ODDS_MARKER: re.Pattern` (`<<ODDS (\d+)>>`).
- `needs_preview(check: dict) -> bool`: `difficulty != "routine"`.
- `lock(seen: dict[str, dict], check: dict) -> dict`: returns the check with the first-seen stat's `difficulty` and `challenge_tier`, and adds the stat to `seen` (in place) when it is new. Callers validate with `check_preview` first, so a refused check never fixes a stat.
- `chance(state, data, check) -> str`: "38%", "sure" or "no chance", from `check_preview`. `app.odds_text` and `Session.chance` call it instead of their own copies.
- `preview_text(state, data, check) -> str`: "Agility check, hard: 38%".
- `stamp_odds(narration, state, data) -> tuple[str, list[int], list[int]]`: the stamped text, the action numbers shown, and the out-of-range numbers (removed from the text, with the space before each).

`Session` calls these and keeps its side files (`previews.json`, `shown.json`). `Game` keeps `seen` in memory for the current turn number.

**Session play** (`ui/cli/session.py`):

- `Pending` gains `rejections: dict[str, int]` (tool name, or `"prose"`) and `dropped: list[dict]` (`{"name", "args"}`), both defaulting empty so a pending file from before M2b still loads.
- `tool`: a rejection of an offered tool (from `apply_tool`, from `check_preview` on the preview path, or unparseable JSON) adds 1, saves `Pending`, and prints "Rejected (2 retries left): reason", then "(1 retry left)". The third adds `{"name", "args"}` (that call's args) to `dropped` once and prints "<tool> is dropped for this turn (NAR-06); carry on without it." Any later call to it prints the same and is not applied. `offered` leaves dropped tools out.
- `narrate`: a rejection adds 1 to `"prose"`, also when it would have replaced accepted prose. At 3 with no accepted prose, it says `session commit` now saves a fallback turn. A later accepted `narrate` still sets the prose, and then `commit` is normal.
- `commit`: emits one `tool_call_dropped` event per `dropped` entry. If `narration` is None and `"prose"` ≥ 3, it commits `fallback.render(sim)` with `is_fallback = True` and every accepted event, without emitting `actions_suggested` (the old ones stay). If prose exists and `suggest_actions` is dropped, it emits `actions_suggested` with `[]` and strips all markers. Otherwise as today.

**`pantheon play`** (`narrator/loop.py`, `ui/cli/app.py`):

- `take_turn` gains `locks: dict[str, dict] | None = None` (the turn's `seen`, which `Game` owns and clears when the turn number changes) and `previewed: bool = False`. In the referee step, with `locks` given and no fight on, each `request_check` call is first checked with `check_preview`. A refusal is a rejection, counted and returned to the model as today. Then it is locked with `preview.lock`. If `needs_preview`, the referee stops before `apply_tool`, and `take_turn` returns at once with `TurnOutcome.preview` set to the locked check, `narration` "", no events, and the input `state` and `rng_state`. Otherwise the locked check (Routine) rolls as today.
- With `previewed=True`, the referee never runs. If the chosen check is refused when rolled, the turn goes on with no roll (NAR-08: nothing the player did not see may roll).
- The loop strips `ODDS_MARKER` before `prose_problems` and `repeats_earlier_turn`. After the scribe, and only for non-fallback prose, it stamps the markers with `preview.stamp_odds` against `sim.state`, removing out-of-range ones and noting them in `log`.
- `Game.turn`: on `outcome.preview`, print `Preview: <preview_text>` and "At stake: <stakes>. Nothing has been rolled yet.", then ask "Go ahead? (y/n)". "y" calls `take_turn` again with `chosen_check` set to the preview, `previewed=True`, and the first pass's tokens added to the record. Anything else saves nothing and returns to the prompt.
- `_show_actions`: prints the numbered list only in a fight; outside one, the status line and "Type what you do." `run` takes a bare number as a pick only in a fight. `_HELP` and `_COMMANDS` drop "inspect 2" and "a number from the list" outside fights.
- Dual Offer numbering: `offer_start(state)` in `app.py` is `len(state.suggested) + 1` in a fight, else 1. `Game.run`, `Session.menu` and `Session.screen` use it.
- `prompts/narrator.md`: the closing-thought marker rule, so the API narrator writes markers too; the play skill's step 3 points there.

**Build notes (S2, choices the re-check left open):** `Session.tool` now validates a proposed check before locking it. A Routine first preview of a stat also fixes it, so a later Hard proposal of the same stat rolls at once (D-050's rule cuts both ways). The referee stops at the first `request_check` that needs a preview; the others in that reply are ignored. Fight moves are stamped through `check_preview`'s move path. `Session.inspect` is unchanged (it is the narrator's command); only `pantheon play`'s `inspect` is limited to fights. `strip_markers` in `preview.py` handles a turn with no actions.

## Slices

### S1 Session play counts rejections, drops and falls back

- **Morgan tries:** nothing new to see in normal play; a turn can no longer stall on a bad call.
- **Checks that fail now:** J1, J2, J3 checks.
- **Files:** `src/pantheon/ui/cli/session.py`: `Pending` fields, `tool`, `narrate`, `commit`. `src/pantheon/narrator/loop.py`: `run_tools` tries the third call and drops on its rejection. `tests/test_session.py`: the three tests. `.claude/skills/play/SKILL.md`: one line on the retry cap and the fallback. `docs/SPEC.md` NAR-06: a dropped `suggest_actions` leaves no new suggestions. `docs/DECISIONS.md`: D-053.
- **Waits on:** none

### S2 One preview module, and D-050 on `pantheon play`

- **Morgan tries:** `uv run pantheon play` with a key: no menu outside fights, odds in the closing thought, a Hard check asks first.
- **Checks that fail now:** J4, J6 and J7 checks; J5 is a guard that passes now.
- **Files:** `src/pantheon/engine/preview.py` (new) and `tests/engine/test_preview.py`. `ui/cli/session.py`: call the module. `narrator/loop.py`: the gate and stamping. `ui/cli/app.py`: preview prompt, no menu outside fights. `prompts/narrator.md`: the marker rule. `tests/test_play.py`, `tests/narrator/test_loop.py`: new tests, number picks outside fights rewritten as typed text.
- **Waits on:** S1 (both edit `session.commit`; S2 moves S1's marker stripping into `preview.py`).

### S3 Ten scripted turns on each path

- **Morgan tries:** reads `docs/playtests/2026-11-06-m2b-scripted-run.md`, both runs' saved narration.
- **Checks that fail now:** J8 checks.
- **Files:** `tests/test_m2b_scripted_run.py` (new; imports `Game` from `tests/test_session.py`). `docs/playtests/2026-11-06-m2b-scripted-run.md` (new, written by hand from `pytest -s` output of both runs).
- **Waits on:** S1, S2

## Verification

- Every push: `node .claude/master/sync.mjs --check && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest --cov --cov-fail-under=90`
- End to end: `uv run pytest tests/test_m2b_scripted_run.py -v`; the owner's played session after M2d.

## Open questions

- None blocking. D-051 (4) holds the next steps if the closing thought still steers the owner.
