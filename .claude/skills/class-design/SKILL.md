---
name: class-design
description: Design new Pantheon classes, evolved classes or class traits so they stay consistent with the roster (D-042). Use when the owner asks for a new class, a Level 10 evolution, a class rework, or a content batch that adds classes. Not for skills or items alone.
---

# Designing a class

Classes are canon (WLD-03): propose first, write only after the owner approves, and commit with the `canon:` prefix. Read the current roster before designing: `world/data/classes.yaml`, the Classes table in `world/power_tiers.md`, and the gods' `favoured_classes` in `world/data/gods.yaml`.

## 1. Find the gap

- Name the role the roster lacks, in one sentence a player would recognise ("the druid", "a trap-maker"). Classic fantasy roles are a guide; Caldrenne's names and traits are its own. Never copy another game's class name, trait name or mechanic.
- Check the world allows it: no gunpowder, no technology past `00_overview.md`, nothing that touches sealed canon.
- If two existing classes already cover the role between them, say so and propose a tweak instead of a new class.

## 2. Fill the fields

| Field | Rule |
|---|---|
| `id` | lowercase, underscores, unique |
| `name` | one or two words, reads as a job or a title |
| `primary` / `secondary` | two different stats; check the roster's spread so no stat leads fewer than three classes |
| `trait` | `Name: effect`, one sentence, the size of the existing traits: a +10 in a situation, a 20 % discount on one skill family, or one action-economy perk, never two of these |
| `blurb` | one line, plain words, what it feels like to play; no pronoun for the player |
| `fragments_to_fuse` | 3 unless the trait says otherwise |

Write the trait so the engine could check it from state (a situation, a skill family, a resource). If it needs something the engine lacks, list that in `docs/canon_gaps.md`.

## 3. Tie it to the world

- Give it one to two favouring gods whose domain and affinities fit; each god favours three or four classes.
- Name the affinities its spells or skills will lean on.
- For an evolution: the base class, the unlock (an affinity rank, an Oath, a stat, a title or a deed, as in the `power_tiers.md` example), and how the trait grows.

## 4. Propose, then write

1. Show the owner a page with the new rows (name, stats, blurb, trait, echoes, gods) beside the roster. Wait for approval.
2. Then update together, in one `canon:` commit: `world/data/classes.yaml`, the Classes table in `world/power_tiers.md`, `favoured_classes` in `world/data/gods.yaml` and `world/pantheon.md`.
3. Update tests that count or name classes; never weaken one (VER-01). Run the local checks in AGENTS.md.
4. Record the decision in `docs/DECISIONS.md` if the roster's shape changed.
