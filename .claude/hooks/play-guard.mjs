// Play guard (D-041). While data/.playing exists, this Claude Code session is the narrator, so it may
// see only what the API narrator sees: public files and `pantheon session` output. Secret and sealed
// canon stay out of its context (NAR-02, WLD-04). `uv run pantheon session stop` turns it off.
import { existsSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const root = process.env.CLAUDE_PROJECT_DIR || process.cwd();
if (!existsSync(join(root, "data", ".playing"))) process.exit(0);

const event = JSON.parse(readFileSync(0, "utf8"));
const input = event.tool_input || {};
const STOP = " To work on the code instead, run `uv run pantheon session stop` first.";

// Public reading only: the narrator prompt, public canon at the top of world/, the save folder and this skill.
const READABLE = [/^prompts\/[^/]+$/, /^world\/[^/]+\.md$/, /^data\//, /^\.claude\/skills\/play\//];
// Bash may run the game and the save script, optionally after `cd <dir> &&`, with no other chaining.
const BASH = /^(?:cd\s+\S+\s*&&\s*)?(?:uv run (?:-q )?pantheon session(?:\s[^;&|<>`$\n]*)?|scripts\/saves\.sh (?:pull|push))$/;

function inside(path) {
  const rel = relative(root, resolve(root, path)).replaceAll("\\", "/");
  return rel.startsWith("..") ? null : rel;
}

function verdict() {
  switch (event.tool_name) {
    case "Bash":
      return BASH.test((input.command || "").trim()) && !/secret|sealed/i.test(input.command) ? null : "During play, Bash runs only `uv run pantheon session ...` and `scripts/saves.sh`.";
    case "Read": {
      const rel = inside(input.file_path || "");
      return rel !== null && READABLE.some((r) => r.test(rel)) ? null : "During play, only public files may be read (prompts/, world/*.md, data/, the play skill).";
    }
    case "Write":
    case "Edit": {
      const rel = inside(input.file_path || "");
      return rel !== null && rel.startsWith("data/") ? null : "During play, only files under data/ may be written.";
    }
    case "Grep":
    case "Glob":
    case "Agent":
    case "NotebookEdit":
      return `During play, ${event.tool_name} is off: it could reach secret or sealed canon.`;
    default:
      return null;
  }
}

const reason = verdict();
if (reason) {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: reason + STOP },
    }),
  );
}
