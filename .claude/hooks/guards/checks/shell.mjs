// Shell checks. Each check: { id, rule, tools, mode?, test(input, facts) → message | null }.
// Synced from AI-Master-Instructions (hook/guards); edit it there.
import path from 'node:path';
import { gitSubcommand, lists, operands, parse } from '../parse.mjs';

/** True for -f, --full, or a short-flag group containing f (-fx). */
const fullMatch = (args) => args.some((a) => a === '--full' || /^-[A-Za-z0-9]*f[A-Za-z0-9]*$/.test(a));

/** Script and target names that read as a check (`npm run check`, `make test`, `node scripts/verify.mjs`). */
const CHECK_NAME = /(^|[^a-z])(test|tests|check|checks|lint|verify|validate|typecheck|type-check|ci)([^a-z]|$)/i;
/** Check tools run directly or through npx, `pnpm exec`, `python -m` and the like. */
const CHECK_TOOLS = new Set(['vitest', 'jest', 'mocha', 'ava', 'tap', 'playwright', 'cypress', 'tsc', 'eslint', 'biome', 'pytest', 'py.test', 'tox', 'nox', 'ruff', 'mypy', 'flake8', 'pylint', 'shellcheck', 'unittest']);
const RUNNERS = new Set(['npm', 'pnpm', 'yarn', 'bun']);
/** Keywords whose condition consumes the status: `if npm test; then …` is a deliberate test. */
const CONDITIONS = new Set(['if', 'elif', 'while', 'until']);

/** The words a tool runs as: `npx vitest run` → ['vitest', 'run']. */
function viaRunner(args) {
  const words = operands(args.filter((a) => !/^--?(yes|no-install|quiet|silent)$/.test(a)));
  return words;
}

/** A label like `npm test` when the simple command is a recognised check, else null. */
export function checkLabel(c) {
  const { name, args } = c;
  if (name === 'timeout') {
    const rest = operands(args, new Set(['-s', '--signal', '-k', '--kill-after'])).slice(1);
    return rest.length ? checkLabel({ name: path.basename(rest[0]), args: rest.slice(1) }) : null;
  }
  if (RUNNERS.has(name)) {
    const [sub, script] = operands(args);
    if (sub === 'test' || sub === 't') return `${name} test`;
    if ((sub === 'run' || sub === 'run-script') && script && CHECK_NAME.test(script)) return `${name} run ${script}`;
    if ((sub === 'exec' || sub === 'dlx' || sub === 'x') && script && CHECK_TOOLS.has(script)) return `${name} ${sub} ${script}`;
    if (name !== 'npm' && sub && sub !== 'install' && sub !== 'add' && CHECK_NAME.test(sub)) return `${name} ${sub}`;
    return null;
  }
  if (name === 'npx' || name === 'bunx') {
    const [tool] = viaRunner(args);
    return tool && CHECK_TOOLS.has(tool.replace(/@[^/]*$/, '')) ? `${name} ${tool}` : null;
  }
  if (name === 'node' || name === 'deno') {
    if (args.includes('--test') || args[0] === 'test') return `${name} ${args.includes('--test') ? '--test' : 'test'}`;
    const [script] = operands(args);
    return script && CHECK_NAME.test(path.basename(script)) ? `${name} ${script}` : null;
  }
  if (/^python(\d(\.\d+)?)?$/.test(name)) {
    const m = args.indexOf('-m');
    if (m >= 0 && CHECK_TOOLS.has(args[m + 1])) return `${name} -m ${args[m + 1]}`;
    const [script] = operands(args);
    return script && script !== '-' && CHECK_NAME.test(path.basename(script)) ? `${name} ${script}` : null;
  }
  if (CHECK_TOOLS.has(name)) return name;
  if (name === 'cargo' || name === 'go') {
    const [sub] = operands(args);
    return ['test', 'check', 'clippy', 'vet'].includes(sub) ? `${name} ${sub}` : null;
  }
  if (name === 'make' || name === 'just') {
    const target = operands(args, new Set(['-C', '-f', '-j'])).find((a) => !a.includes('='));
    return target && CHECK_NAME.test(target) ? `${name} ${target}` : null;
  }
  if (name === 'prettier' && args.includes('--check')) return 'prettier --check';
  if ((name === 'bash' || name === 'sh') && args[0] && !args[0].startsWith('-') && CHECK_NAME.test(path.basename(args[0]))) return `${name} ${args[0]}`;
  if (name.startsWith('./') || /\.(sh|mjs|js|py)$/.test(name)) return CHECK_NAME.test(path.basename(name)) ? name : null;
  return null;
}

/** `git commit` or `git push`, else null. */
function gitTarget(c) {
  if (c.name !== 'git') return null;
  const { sub } = gitSubcommand(c.args);
  return sub === 'commit' || sub === 'push' ? `git ${sub}` : null;
}

/** Apply a `set` command to the shell options we track. */
function applySet(c, opts) {
  for (let i = 0; i < c.args.length; i++) {
    const a = c.args[i];
    const on = a.startsWith('-');
    if (a === '-o' || a === '+o') {
      const o = c.args[++i];
      if (o === 'errexit') opts.errexit = on;
      if (o === 'pipefail') opts.pipefail = on;
    } else if (/^[-+][a-zA-Z]+$/.test(a)) {
      if (a.includes('e')) opts.errexit = on;
      // `set -euo pipefail`: an `o` in the group takes the next word as the option's name.
      if (a.includes('o') && c.args[i + 1] === 'pipefail') opts.pipefail = on;
      if (a.includes('o')) i += 1;
    }
  }
}

const EXITS = new Set(['exit', 'return']);
const TESTS = new Set(['test', '[', '[[']);
const STATUS = /\$\?|\$\{\?\}|PIPESTATUS/;

/** True when the target at k runs only after an explicit status test: `[ $? -eq 0 ] && git push`, `if test ${PIPESTATUS[0]} …; then git push`. */
function statusTested(list, k) {
  let m = k;
  while (m > 0 && list[m].op === '&&') m -= 1;
  const guards = [list[m]];
  if (list[m].head === 'then' && m > 0) guards.push(list[m - 1]);
  return guards.some((g) => g.commands.some((c) => TESTS.has(c.name) && STATUS.test(c.args.join(' '))));
}

/**
 * Where a check's failure stops counting before a `git commit` or `git push` that runs anyway:
 * { check, lost, target } or null. Reads one list (see `lists` in parse.mjs).
 */
export function lostCheck(list) {
  const opts = { errexit: false, pipefail: false };
  for (let i = 0; i < list.length; i++) {
    const item = list[i];
    for (const c of item.commands) if (c.name === 'set') applySet(c, opts);
    const at = item.commands.find((c) => checkLabel(c));
    if (!at || CONDITIONS.has(item.head)) continue;
    const check = checkLabel(at);
    const last = item.commands.filter((c) => c.pipeline === at.pipeline).at(-1);
    let lost = null;
    let j = i;
    if (item.head === '!') lost = '!';
    else if (last !== at && !opts.pipefail) lost = `| ${last.name}`;
    else {
      // Follow the `&&` chain: the check still guards what it reaches.
      while (j + 1 < list.length && list[j + 1].op === '&&') {
        j += 1;
        // `check && { a; b; }`: the whole group runs only when the check passed.
        const d = list[j].depth;
        if (d > list[j - 1].depth) while (j + 1 < list.length && list[j + 1].depth >= d) j += 1;
      }
      const next = list[j + 1];
      if (!next) continue;
      if (next.op === '||') {
        if (EXITS.has(next.commands[0]?.name)) continue;
        lost = '||';
      } else if (next.op === '&') lost = '&';
      else if (opts.errexit && j === i) continue; // `set -e` stops the shell on the check itself
      else lost = next.op === '\n' ? 'a new line' : next.op;
    }
    for (let k = j + 1; k < list.length; k++) {
      const target = list[k].commands.map(gitTarget).find(Boolean);
      if (target) return statusTested(list, k) ? null : { check, lost, target };
    }
  }
  return null;
}

export const checks = [
  {
    id: 'shell.pkill',
    rule: 'lesson adventure-manager :12',
    tools: ['Bash'],
    // Denied, not warned: a warning arrives after the command, and by then the shell is dead (D-023).
    mode: 'ask', // D-037
    test(input) {
      const command = input.tool_input?.command;
      if (typeof command !== 'string') return null;
      const hit = parse(command).some((c) => c.name === 'pkill' && fullMatch(c.args));
      return hit ? 'stop runs by PID from `ps -eo pid,args`' : null;
    },
  },
  {
    // Warn only (D-064): the command has already run when Claude reads this, so it says what to redo.
    id: 'shell.chain',
    rule: 'VER-02',
    tools: ['Bash'],
    test(input) {
      const command = input.tool_input?.command;
      if (typeof command !== 'string') return null;
      for (const list of lists(command)) {
        const hit = lostCheck(list);
        if (hit) {
          const how = hit.lost.startsWith('|') ? `the pipe into \`${hit.lost.slice(2)}\` keeps its status, not the check's` : `\`${hit.lost}\` drops its status`;
          return `\`${hit.target}\` runs even when \`${hit.check}\` fails: ${how}. Check that it passed; next time join with \`&&\`, or \`set -o pipefail\` before a pipe`;
        }
      }
      return null;
    },
  },
];
