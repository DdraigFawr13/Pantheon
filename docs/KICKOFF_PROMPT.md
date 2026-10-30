# Kickoff prompt

Paste the block below as the first message in Claude Code, opened in this repository.

```
Read AGENTS.md and follow its read order (HANDOFF, DECISIONS, SPEC, architecture, roadmap). Open world/ files when the milestone needs them; M0 needs only their frontmatter.

Then execute milestone M0, and continue into M1 without waiting for approval if M0 acceptance criteria pass.

Constraints:
- Follow docs/SPEC.md section 5 exactly. Record every assumption in docs/DECISIONS.md.
- Write failing tests before engine code. Cite requirement IDs in test names.
- The engine package shall not import from narrator, llm, or ui.
- Do not modify world/ files. List any canon gaps you find in docs/canon_gaps.md.
- Never place secret lore from world/secret/ in any prompt, log line, or test fixture that is not specifically testing the reveal gate.

At the end of each milestone, report: requirements satisfied, requirements deferred, known defects, and the exact command to run the result.
```
