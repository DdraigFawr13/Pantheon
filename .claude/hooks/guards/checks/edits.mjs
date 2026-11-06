// Edit scripts that change nothing (lesson riftfront :8): `sed -i`, `perl -i`, `ruby -i`, and Python or Node
// one-liners that write files. `edit.record` (PreToolUse) hashes the files a Bash call will edit and
// notes them in the session file; `edit.noop` (PostToolUse) hashes them again and warns when none
// changed but at least one was rewritten (a file only read was not an edit target). Warn only; never asks (D-064). Synced from AI-Master-Instructions (hook/guards); edit it there.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { parse } from '../parse.mjs';
import { updateSession } from '../lib.mjs';

/** Limits, so a hook call stays fast: files per call, bytes per file, records kept, record age. */
export const MAX_FILES = 50;
export const MAX_BYTES = 5 * 1024 * 1024;
export const MAX_RECORDS = 10;
export const MAX_AGE_S = 30 * 60;

const PY = /^python(\d(\.\d+)?)?$/;
/** Text in a one-liner that writes a file. */
const WRITES = /write_text|write_bytes|\.write\(|writeFileSync|writeFile\(|appendFileSync|open\([^)]*,\s*(mode\s*=\s*)?['"][wax]/;
/** Quoted words in a script that look like file paths: a name with an extension, or a path with a slash. */
const QUOTED_PATH = /(['"])(\/?(?:[\w.@-]+\/)*[\w@-][\w.@-]*\.[A-Za-z0-9]+)\1/g;

/**
 * The files a `sed`, `perl` or `ruby` call edits in place, or null when it doesn't edit in place.
 * `-i` may be grouped (`-pi`, `-Ei`) or carry a backup suffix (`-i.bak`, `-i ''` on macOS).
 */
export function inPlaceFiles(name, args) {
  if (name !== 'sed' && name !== 'perl' && name !== 'ruby') return null;
  let inPlace = false;
  let script = false;
  const ops = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--') {
      ops.push(...args.slice(i + 1));
      break;
    }
    if (a === '--in-place' || a.startsWith('--in-place=')) inPlace = true;
    else if (a === '--expression' || a === '--file') {
      script = true;
      i += 1;
    } else if (a.startsWith('--expression=') || a.startsWith('--file=')) script = true;
    else if (/^-[A-Za-z0-9]/.test(a) && !a.startsWith('--')) {
      const at = a.indexOf('i');
      const flags = at >= 0 ? a.slice(1, at) : a.slice(1);
      if (at >= 0) {
        inPlace = true;
        // macOS `sed -i '' …`: an empty word after a bare -i is its suffix.
        if (a === '-i' && args[i + 1] === '') i += 1;
      }
      // A group that ends in e (or f for sed) before any -i takes the script as the next word.
      const last = flags.at(-1);
      if (at < 0 && (last === 'e' || last === 'E' || (name === 'sed' && last === 'f'))) {
        script = true;
        i += 1;
      } else if (at < 0 && (flags.includes('e') || flags.includes('E'))) script = true;
    } else if (!a.startsWith('-')) ops.push(a);
  }
  if (!inPlace) return null;
  return script ? ops : ops.slice(1);
}

/** The script text of a Python or Node call that runs code from the command line or stdin, else null. */
function inlineScript(c, command) {
  if (PY.test(c.name)) {
    const at = c.args.indexOf('-c');
    if (at >= 0) return c.args[at + 1] ?? '';
  } else if (c.name === 'node') {
    const at = c.args.findIndex((a) => a === '-e' || a === '--eval' || a === '-p' || a === '--print');
    if (at >= 0) return c.args[at + 1] ?? '';
  } else return null;
  // `python3 - <<'EOF'` or `node <<EOF`: the program comes from a heredoc, which `parse` doesn't keep.
  const scriptArg = c.args.find((a) => !a.startsWith('-'));
  return scriptArg === undefined && /<</.test(command) ? command : null;
}

/** Expand a simple `dir/*.md` pattern (wildcards in the last part only). Other words come back as they are. */
function expand(word, dir) {
  const base = path.basename(word);
  if (!/[*?]/.test(base) || /[*?[]/.test(path.dirname(word))) return [word];
  const folder = path.resolve(dir, path.dirname(word));
  const re = new RegExp(`^${base.replace(/[.+^${}()|\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.')}$`);
  try {
    return fs.readdirSync(folder).filter((f) => re.test(f) && !f.startsWith('.')).map((f) => path.join(path.dirname(word), f));
  } catch {
    return [];
  }
}

/** { tool, files: [{ arg, abs }] } for each simple command that edits files, with each file's absolute path. */
export function edits(command, cwd, commands = parse(command)) {
  const out = [];
  for (const c of commands) {
    const dir = c.dir ?? cwd;
    let words = inPlaceFiles(c.name, c.args);
    let tool = words ? `${c.name} -i` : null;
    let created = false;
    if (!words) {
      const script = inlineScript(c, command);
      if (script === null || !WRITES.test(script)) continue;
      words = [...script.matchAll(QUOTED_PATH)].map((m) => m[2]);
      tool = `${c.name} ${PY.test(c.name) ? '-c' : '-e'}`;
      if (script === command) tool = `${c.name} <<`;
      created = true; // a one-liner may create a file it names
    }
    const files = words.flatMap((w) => (/^[~$]/.test(w) ? [] : expand(w, dir))).map((w) => ({ arg: w, abs: path.resolve(dir, w) }));
    if (files.length) out.push({ tool, files, created });
  }
  return out;
}

/** A file's sha1, or null when it is missing, not a file, or larger than MAX_BYTES. */
export function hashFile(abs) {
  try {
    const st = fs.statSync(abs);
    if (!st.isFile() || st.size > MAX_BYTES) return st.isFile() ? `size:${st.size}:${st.mtimeMs}` : null;
    return crypto.createHash('sha1').update(fs.readFileSync(abs)).digest('hex');
  } catch {
    return null;
  }
}

/**
 * When the file was last written: inode, mtime and ctime, or null when it is missing. `sed -i` and
 * `write_text` rewrite a file even when nothing matched; a file a script only read keeps its stamp.
 */
export function stamp(abs) {
  try {
    const st = fs.statSync(abs);
    return `${st.ino}:${st.mtimeMs}:${st.ctimeMs}`;
  } catch {
    return null;
  }
}

const key = (input) => (typeof input?.tool_use_id === 'string' && input.tool_use_id ? input.tool_use_id : 'last');
const now = () => Math.floor(Date.now() / 1000);

export const checks = [
  {
    id: 'edit.record',
    rule: 'lesson riftfront :8',
    events: ['PreToolUse'],
    tools: ['Bash'],
    test(input, facts) {
      const command = input.tool_input?.command;
      if (typeof command !== 'string' || !facts?.session) return null;
      const found = edits(command, facts.cwd, facts.commands());
      if (!found.length) return null;
      const files = {};
      for (const e of found) {
        for (const f of e.files) {
          if (Object.keys(files).length >= MAX_FILES) break;
          const rel = facts.rel(f.abs) ?? f.abs;
          const hash = hashFile(f.abs);
          // A one-liner's quoted names may be files it only reads or creates; a missing one counts as changed if it appears.
          if (hash !== null || e.created) files[rel] = { abs: f.abs, hash, stamp: stamp(f.abs) };
        }
      }
      if (!Object.keys(files).filter((r) => files[r].hash !== null).length) return null;
      const t = now();
      const kept = Object.entries(facts.session.edits ?? {})
        .filter(([, r]) => t - r.ts < MAX_AGE_S)
        .slice(-(MAX_RECORDS - 1));
      updateSession(facts, { edits: Object.fromEntries([...kept, [key(input), { ts: t, tool: found.map((e) => e.tool).join(', '), files }]]) });
      return null;
    },
  },
  {
    id: 'edit.noop',
    rule: 'lesson riftfront :8',
    events: ['PostToolUse'],
    tools: ['Bash'],
    test(input, facts) {
      const records = facts?.session?.edits;
      const k = key(input);
      const record = records?.[k];
      if (!record) return null;
      const rest = { ...records };
      delete rest[k];
      updateSession(facts, { edits: rest });
      const names = Object.keys(record.files);
      const changed = names.some((r) => hashFile(record.files[r].abs) !== record.files[r].hash);
      // Rewritten with the same content: the no-op's signature. A file only read was never written.
      const shown = names.filter((r) => record.files[r].hash !== null && stamp(record.files[r].abs) !== record.files[r].stamp);
      if (changed || !shown.length) return null;
      const list = shown.slice(0, 3).map((r) => `\`${r}\``).join(', ') + (shown.length > 3 ? ` and ${shown.length - 3} more` : '');
      return `\`${record.tool}\` changed none of ${list}: the pattern matched nothing. Check the pattern against the file before going on`;
    },
  },
];
