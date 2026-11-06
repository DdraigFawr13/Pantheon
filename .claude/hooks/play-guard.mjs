// Play guard (D-041). While data/.playing exists, this Claude Code session is the narrator, so it may
// see only what the API narrator sees: public files and `pantheon session` output. Secret and sealed
// canon stay out of its context (NAR-02, WLD-04). `uv run pantheon session stop` turns it off.
// It runs on every tool call (matcher "*") and denies by default: a tool not named below is off during play.
import { existsSync, readFileSync, realpathSync } from "node:fs";
import { homedir } from "node:os";
import { basename, dirname, join, relative, resolve } from "node:path";

const STOP = " To work on the code instead, run `uv run pantheon session stop` first.";
const root = real(process.env.CLAUDE_PROJECT_DIR || process.cwd());

function deny(reason) {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: reason + STOP },
    }),
  );
}

// The real path, following symlinks; for a file not yet written, its real folder plus its name.
function real(path) {
  const full = resolve(path);
  try {
    return realpathSync(full);
  } catch {
    try {
      return join(realpathSync(dirname(full)), basename(full));
    } catch {
      return full;
    }
  }
}

// The path relative to the project root, with forward slashes, or null when it is outside the root.
function inside(path) {
  if (!path) return null;
  const rel = relative(root, real(resolve(root, path))).replaceAll("\\", "/");
  return rel === "" || rel.startsWith("..") || /^[a-zA-Z]:/.test(rel) ? null : rel;
}

// Public reading only: the narrator prompt, public canon at the top of world/, the save folder and this skill.
const READABLE = [/^prompts\/[^/]+$/, /^world\/[^/]+\.md$/, /^data\//, /^\.claude\/skills\/play\//];
// Session steps the play skill uses. `export` and `import` replace or write saves, so only scripts/saves.sh runs them.
const STEPS = new Set(["start", "stop", "status", "prompt", "tools", "setup", "create", "begin", "tool", "narrate",
  "commit", "abandon", "go", "choose", "trial", "use", "equip", "unequip", "sheet", "hooks", "screen", "inspect"]);
// Tools that read or write no project file.
const HARMLESS = new Set(["ArtifactComments", "AskUserQuestion", "ToolSearch", "TodoWrite", "TaskCreate", "TaskUpdate",
  "TaskList", "TaskGet", "ReadNotifications"]);

// Split a command into shell words. Null when any character could run another command or expand a path:
// operators, redirects, substitution, globs and escapes outside single quotes; `$`, backticks and `\` in double quotes.
function words(command) {
  const out = [];
  let word = "";
  let started = false;
  let quote = null;
  for (const ch of command) {
    if (quote === "'") {
      if (ch === "'") quote = null;
      else word += ch;
      continue;
    }
    if (quote === '"') {
      if (ch === '"') quote = null;
      else if ("$`\\".includes(ch)) return null;
      else word += ch;
      continue;
    }
    if (ch === "'" || ch === '"') {
      quote = ch;
      started = true;
    } else if (ch === " " || ch === "\t") {
      if (started) out.push(word);
      word = "";
      started = false;
    } else if (/[;&|<>()`$\\*?[\]{}~!#\n\r]/.test(ch)) {
      return null;
    } else {
      word += ch;
      started = true;
    }
  }
  if (quote) return null;
  if (started) out.push(word);
  return out;
}

function bashAllowed(command) {
  if (/secret|sealed/i.test(command)) return false;
  const w = words(command.trim());
  if (!w || w.length === 0) return false;
  if (w[0] === "scripts/saves.sh") return w.length === 2 && (w[1] === "pull" || w[1] === "push");
  let i = w[0] === "uv" && w[1] === "run" ? 2 : -1;
  if (i < 0) return false;
  if (w[i] === "-q") i++;
  if (w[i] !== "pantheon" || w[i + 1] !== "session" || !STEPS.has(w[i + 2])) return false;
  // Steps that take a file read or write it only in the save folder.
  const file = w.indexOf("--file");
  if (file >= 0 && !(inside(w[file + 1]) || "").startsWith("data/")) return false;
  if (w[i + 2] === "narrate" || w[i + 2] === "screen") {
    const rel = inside(w[i + 3]);
    return w.length === i + 4 && rel !== null && rel.startsWith("data/");
  }
  return true;
}

// Long output of an allowed command, which Claude Code saves under ~/.claude/projects/<project>/<session>/tool-results/.
function savedOutput(path) {
  const projects = real(join(homedir(), ".claude", "projects"));
  const rel = relative(projects, real(path)).replaceAll("\\", "/");
  return /^[^/.][^/]*\/[^/.][^/]*\/tool-results\/[^/]+\.txt$/.test(rel);
}

function verdict(event) {
  const input = event.tool_input || {};
  const tool = event.tool_name;
  if (HARMLESS.has(tool)) return null;
  switch (tool) {
    case "Bash":
      return bashAllowed(input.command || "") ? null : "During play, Bash runs only `uv run pantheon session <step>` and `scripts/saves.sh pull|push`.";
    case "Read": {
      if (input.file_path && savedOutput(input.file_path)) return null;
      const rel = inside(input.file_path);
      return rel !== null && READABLE.some((r) => r.test(rel)) ? null : "During play, only public files may be read (prompts/, world/*.md, data/, the play skill).";
    }
    case "Write":
    case "Edit": {
      const rel = inside(input.file_path);
      return rel !== null && rel.startsWith("data/") ? null : "During play, only files under data/ may be written.";
    }
    case "ArtifactData": {
      // The game page's screen doc. A file sent to the page's database must come from the save folder.
      const files = [input.file_path, ...(input.writes || []).map((w) => w && w.file_path)].filter(Boolean);
      return files.every((f) => (inside(f) || "").startsWith("data/")) ? null : "During play, ArtifactData sends only files under data/.";
    }
    default:
      return `During play, ${tool} is off: it could reach secret or sealed canon.`;
  }
}

if (existsSync(join(root, "data", ".playing"))) {
  try {
    const reason = verdict(JSON.parse(readFileSync(0, "utf8")));
    if (reason) deny(reason);
  } catch (err) {
    deny(`The play guard could not read this call (${err && err.message}), so it is refused.`);
  }
}
