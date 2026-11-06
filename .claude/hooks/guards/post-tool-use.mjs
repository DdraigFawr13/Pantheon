#!/usr/bin/env node
// PostToolUse hook: checks that compare a tool call's effect with what it looked like it would do
// (`edit.noop`). Warns only, through additionalContext. Fails open. Synced from AI-Master-Instructions (hook/guards).
try {
  const { main } = await import('./lib.mjs');
  const { POST_TOOL_USE, urls } = await import('./modules.mjs');
  await main('PostToolUse', urls(POST_TOOL_USE));
} catch (err) {
  const line = String(err?.message ?? err).split('\n')[0];
  process.stdout.write(JSON.stringify({ systemMessage: `ai-master-guard error: ${line}; check skipped` }));
}
process.exitCode = 0;
