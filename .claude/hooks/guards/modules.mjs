// The PreToolUse and PostToolUse check modules, as paths relative to this file. The entry points run them;
// Synced from AI-Master-Instructions (hook/guards); edit it there.
export const PRE_TOOL_USE = ['./checks/shell.mjs', './checks/secrets.mjs', './checks/git.mjs', './checks/synced.mjs', './checks/tests.mjs', './checks/ci.mjs', './checks/edits.mjs'];
export const POST_TOOL_USE = ['./checks/edits.mjs'];

export const urls = (list) => list.map((p) => new URL(p, import.meta.url).href);
