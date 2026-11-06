// The done-gate, run by the Stop hook: gate.page (WS-08), gate.handoff (CTX-03) and gate.ci (CI-07).
// Each nudges once: on the stop that follows a nudge (stop_hook_active) all stay quiet, and
// gate.handoff nudges once per commit (the session file's `nudged` list), gate.ci once per push
// or ready mark (`ciNudged`).
// Synced from AI-Master-Instructions (hook/guards); edit it there.
import fs from 'node:fs';
import path from 'node:path';
import { updateSession } from '../lib.mjs';

const ARTIFACT = /https:\/\/claude\.ai\/(code\/)?artifact\//;
const URL_RE = /https?:\/\/\S+/g;
/** About one and a half phone screens (assumption; the warn release tunes it). */
export const PAGE_WORDS = 250;

/** How many of the session's newest own commits count for HANDOFF. */
export const HANDOFF_COMMITS = 3;

/**
 * Text with fenced blocks removed, fence lines included. A fence opens on a line whose trimmed text
 * starts with 3 or more backticks or tildes, and closes on the next line whose trimmed text is that
 * character repeated at least as many times, or at the end. Inline backticks are kept.
 */
export function withoutFences(text) {
  const out = [];
  let fence = null;
  for (const line of text.split('\n')) {
    const t = line.trim();
    if (fence) {
      if (new RegExp(`^\\${fence[0]}{${fence.length},}$`).test(t)) fence = null;
      continue;
    }
    const open = t.match(/^(`{3,}|~{3,})/);
    if (open) fence = open[1];
    else out.push(line);
  }
  return out.join('\n');
}

/** Why a reply should have been a page, or null. URLs and fenced blocks are removed first. */
export function pageReason(message) {
  const text = withoutFences(message).replace(URL_RE, ' ');
  const words = text.split(/\s+/).filter(Boolean).length;
  if (words >= PAGE_WORDS) return `has ${words} words`;
  const lines = text.split('\n');
  for (let i = 0; i + 1 < lines.length; i++) {
    if (/^\s*\|.*\|\s*$/.test(lines[i]) && /^[\s|:-]+$/.test(lines[i + 1]) && /-/.test(lines[i + 1]) && /\|/.test(lines[i + 1])) return 'has a table';
  }
  return null;
}

/**
 * The session's own commits on the first-parent line: { newest: { sha, subject } or null, shas: [sha…] }.
 * `shas` holds up to HANDOFF_COMMITS newest own commits plus the other commits newer than the newest one.
 */
function ownCommits(facts, start) {
  const range = start.head ? [`${start.head}..HEAD`] : ['-n', '50', 'HEAD'];
  const out = facts.git(['log', '--first-parent', '--format=%H %ce %ct %s', ...range]);
  if (!out) return { newest: null, shas: [] };
  const email = facts.userEmail?.toLowerCase();
  const rows = out.split('\n').map((l) => {
    const [sha, ce, ct, ...subject] = l.split(' ');
    return { sha, ce: ce.toLowerCase(), ct: Number(ct), subject: subject.join(' ') };
  });
  const own = (r) => (!email || r.ce === email) && r.ct >= start.ts;
  const first = rows.findIndex(own);
  if (first < 0) return { newest: null, shas: [] };
  const mine = rows.filter(own).slice(0, HANDOFF_COMMITS).map((r) => r.sha);
  return { newest: rows[first], shas: [...rows.slice(0, first).map((r) => r.sha), ...mine] };
}

/** Whether a commit changed `file` against its first parent (true, false, or null for "can't confirm"). */
function touches(facts, sha, file) {
  // `diff-tree -m --first-parent` still diffs a merge against every parent (git 2.43), so diff
  // against the first parent directly; a root commit has none.
  const parents = facts.git(['rev-list', '--parents', '-n', '1', sha]);
  if (parents === null) return null;
  const out = parents.split(' ').length > 1
    ? facts.git(['diff', '--no-renames', '--name-only', `${sha}^1`, sha])
    : facts.git(['diff-tree', '--root', '--no-commit-id', '--name-only', '-r', sha]);
  return out === null ? null : out.split('\n').includes(file);
}

/**
 * A read of check runs this long after the push counts as CI-07's later check (assumption: CI here
 * takes a few minutes, so a read right after the push sees only pending runs).
 */
export const READ_AFTER_S = 120;

/** Files under `dir`, recursively; [] when it doesn't exist. */
function filesUnder(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    return e.isDirectory() ? filesUnder(p) : [p];
  });
}

/**
 * The session's newest push: { ref, sha, ts } or null. Read from git's reflogs of the remote-tracking
 * refs, where `git push` writes "update by push" (a stable on-disk format; transcripts are not read,
 * harness-release-a.md "Reading transcripts"). Pushes before `since` (unix seconds) are ignored.
 */
export function lastPush(facts, since) {
  if (!facts.stateDir) return null;
  const logs = path.join(path.dirname(facts.stateDir), 'logs', 'refs', 'remotes');
  let best = null;
  for (const file of filesUnder(logs)) {
    for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
      const m = line.match(/^[0-9a-f]+ ([0-9a-f]+) .*> (\d+) [+-]\d{4}\tupdate by push/);
      if (!m) continue;
      const ts = Number(m[2]);
      if (ts >= since && (!best || ts >= best.ts)) best = { ref: path.relative(logs, file).split(path.sep).join('/'), sha: m[1], ts };
    }
  }
  return best;
}

const hhmm = (ts) => new Date(ts * 1000).toISOString().slice(11, 16);

export const checks = [
  {
    id: 'gate.page',
    rule: 'WS-08',
    test(input, facts) {
      if (input.stop_hook_active === true || facts?.env?.CLAUDE_CODE_REMOTE !== 'true') return null;
      // Headless runs (evals, scripts) have no one reading on a phone.
      if (facts.env.AI_MASTER_HEADLESS === '1') return null;
      const message = input.last_assistant_message;
      if (typeof message !== 'string' || ARTIFACT.test(message)) return null;
      const reason = pageReason(message);
      return reason && `the reply ${reason} and no artifact link: publish what Morgan must read as a page and link it`;
    },
  },
  {
    id: 'gate.handoff',
    rule: 'CTX-03',
    test(input, facts) {
      if (input.stop_hook_active === true || !facts) return null;
      const handoff = facts.handoff;
      const start = handoff && facts.session;
      if (!start) return null;
      const { newest, shas } = ownCommits(facts, start);
      if (!newest) return null;
      const nudged = Array.isArray(start.nudged) ? start.nudged : [];
      if (nudged.includes(newest.sha)) return null;
      // Any "can't confirm" (null) from git lets the gate pass.
      for (const sha of shas) if (touches(facts, sha, handoff) !== false) return null;
      const status = facts.git(['status', '--porcelain', '--', handoff]);
      if (status !== '') return null;
      updateSession(facts, { nudged: [...nudged, newest.sha] });
      return `commit ${newest.sha.slice(0, 7)} "${newest.subject}" has no HANDOFF update`;
    },
  },
  {
    id: 'gate.ci',
    rule: 'CI-07',
    test(input, facts) {
      if (input.stop_hook_active === true || !facts || facts.env?.CLAUDE_CODE_REMOTE !== 'true') return null;
      if (facts.env.AI_MASTER_HEADLESS === '1') return null;
      const start = facts.session;
      if (!start) return null;
      const push = lastPush(facts, start.ts);
      const ready = Number.isFinite(start.ciReady) ? start.ciReady : null;
      const usePush = push && (ready === null || push.ts >= ready);
      const at = usePush ? push.ts : ready;
      if (at === null) return null;
      if ((start.ciScheduled ?? -1) >= at || (start.ciRead ?? -1) >= at + READ_AFTER_S) return null;
      const key = usePush ? `push:${push.ref}@${push.sha}` : `ready:${ready}`;
      const nudged = Array.isArray(start.ciNudged) ? start.ciNudged : [];
      if (nudged.includes(key)) return null;
      updateSession(facts, { ciNudged: [...nudged, key].slice(-20) });
      const what = usePush ? `pushed ${push.ref} at ${hhmm(at)} UTC` : `marked a PR ready at ${hhmm(at)} UTC`;
      return `${what} and scheduled no CI check: schedule one about 5 minutes out (send_later) and read the check runs then; don't promise a CI notice`;
    },
  },
];
