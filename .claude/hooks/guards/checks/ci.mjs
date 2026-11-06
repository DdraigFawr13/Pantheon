// CI-07's recorder, run by the PreToolUse hook: notes in the session file when the session schedules
// its own CI check, reads check runs, or marks a PR ready. It never warns; gate.ci (gates.mjs) reads
// the notes at Stop. Synced from AI-Master-Instructions (hook/guards); edit it there.
import { updateSession } from '../lib.mjs';

/** Tools that schedule a later turn in this session (cloud sessions). */
export const SCHEDULERS = ['mcp__claude-code-remote__send_later', 'mcp__claude-code-remote__create_trigger'];
/** Tools that read a PR's check runs. `pull_request_read` counts only for these methods. */
export const CHECK_READERS = ['mcp__github__pull_request_read', 'mcp__github__get_check_run'];
export const CHECK_METHODS = ['get_check_runs', 'get_status'];
export const READY = 'mcp__github__update_pull_request';

/** What a tool call means for CI-07: 'scheduled', 'read', 'ready', or null. */
export function ciEvent(tool, toolInput) {
  if (SCHEDULERS.includes(tool)) return 'scheduled';
  if (tool === 'mcp__github__get_check_run') return 'read';
  if (tool === 'mcp__github__pull_request_read') return CHECK_METHODS.includes(toolInput?.method) ? 'read' : null;
  if (tool === READY) return toolInput?.draft === false ? 'ready' : null;
  return null;
}

/** Session-file keys, one per event: the newest time (unix seconds) the session did it. */
export const KEYS = { scheduled: 'ciScheduled', read: 'ciRead', ready: 'ciReady' };

export const checks = [
  {
    id: 'ci.record',
    rule: 'CI-07',
    tools: [...SCHEDULERS, ...CHECK_READERS, READY],
    test(input, facts) {
      const event = ciEvent(input?.tool_name, input?.tool_input);
      if (event && facts) updateSession(facts, { [KEYS[event]]: Math.floor(Date.now() / 1000) });
      return null;
    },
  },
];
