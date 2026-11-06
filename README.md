# Pantheon (working title)

An open-ended, AI-narrated LitRPG. The player controls one life in a medieval fantasy world governed by gods, oaths, and an explicit ladder of power tiers. Choices are free-text or suggested; consequences persist and branch through world state, not through a hand-drawn tree.

## Design principle

**The engine owns the numbers. The narrator owns the prose.**

- Deterministic Python engine: stats, dice, tiers, XP, inventory, standing, clocks, event log.
- LLM narrator: scenes, dialogue, NPC voice, proposals for state changes via typed tool calls.
- The engine validates every proposal. The narrator never writes state directly.

## Repository layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Agent instructions: read order, local checks, project rules (read first) |
| `CLAUDE.md` | Loads `AGENTS.md` and the shared rules from AI-Master-Instructions |
| `docs/SPEC.md` | Build specification: requirement IDs and working agreements |
| `docs/HANDOFF.md`, `docs/DECISIONS.md`, `docs/LESSONS.md` | Session state, settled decisions, lessons |
| `docs/architecture.md` | Components, data model, turn loop, memory layers, tool contracts |
| `docs/roadmap.md` | Milestones M0 to M6 with acceptance criteria |
| `docs/BUILD_PLAN.md` | Ordered tasks from M0 to the first playable version (M3.5) |
| `prompts/narrator.md` | Runtime system prompt template for the in-game narrator |
| `world/` | Canon: world bible (public lore) |
| `world/secret/` | Canon: narrator-only lore, released through reveal gates |
| `world/sealed/` | Sealed canon the owner does not read (WLD-04) |
| `src/`, `tests/`, `data/` | Code, tests, runtime saves (git-ignored) |

## Status

M1.7 is merged (M1a to M1c, M1.5 to M1.7). Play on the PC with `start.bat` (Claude Haiku through the API), or in a Claude Code session on this repo by saying "play": the session is the narrator, at no API cost (D-041). Next: M1d combat (draft PR #16) in `docs/BUILD_PLAN.md`; `docs/HANDOFF.md` has the current step.

## Configuration

Copy `.env.example` to `.env` and `config.example.toml` to `config.toml`. The model identifier is configuration, never code.
