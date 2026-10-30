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
| `CLAUDE.md` | Build specification and working agreements for Claude Code (read first) |
| `docs/architecture.md` | Components, data model, turn loop, memory layers, tool contracts |
| `docs/roadmap.md` | Milestones M0 to M6 with acceptance criteria |
| `docs/KICKOFF_PROMPT.md` | First message to paste into Claude Code |
| `prompts/narrator.md` | Runtime system prompt template for the in-game narrator |
| `world/` | Canon: world bible (public lore) |
| `world/secret/` | Canon: narrator-only lore, released through reveal gates |
| `src/`, `tests/`, `data/` | Code, tests, runtime saves (git-ignored) |

## Status

Scaffold only. Begin at milestone M0 in `docs/roadmap.md`.

## Configuration

Copy `.env.example` to `.env` and `config.example.toml` to `config.toml`. The model identifier is configuration, never code.
