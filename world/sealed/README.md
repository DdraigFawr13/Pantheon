# Sealed canon

Files in this folder (and in `src/pantheon/sealed/` once code exists) hold canon the owner has chosen not to read (D-012). Everything else about them is normal canon: Markdown with frontmatter (WLD-01), `type: sealed-lore`, `visibility: secret`, a `reveal_gate`, read-only at runtime. Sealed flags are listed in `data/flags.yaml` in this folder (D-024). This README is a folder note: the loader skips it.

Rules:

- The owner approves a spoiler-free outline (recorded in `docs/DECISIONS.md` D-012), not the content.
- An independent reviewer agent checks every change here against public canon in `world/`, the outline (D-012) and the content limits (D-016), and its verdict is summarised in the PR without spoilers.
- A test proves every `reveal_gate` here parses (grammar: `docs/architecture.md` section 7) and that every path in it is a registered flag or a state field.
- Commit messages, PR text, HANDOFF and DECISIONS describe sealed changes only by file name and outline item.
