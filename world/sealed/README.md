# Sealed canon

Files in this folder (and in `src/pantheon/sealed/` once code exists) hold canon the owner has chosen not to read (D-012). Everything else about them is normal canon: Markdown with frontmatter (WLD-01), `visibility: secret`, a `reveal_gate`, read-only at runtime.

Rules:

- The owner approves a spoiler-free outline (recorded in `docs/DECISIONS.md` D-012), not the content.
- An independent reviewer agent checks every change here against public canon in `world/`, the outline and the content limits, and its verdict is summarised in the PR without spoilers.
- A test proves every `reveal_gate` here parses and can be reached by flags the engine can set.
- Commit messages, PR text, HANDOFF and DECISIONS describe sealed changes only by file name and outline item.
