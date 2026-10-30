#!/usr/bin/env bash
# Pantheon cloud-session setup, run by the synced session-start.sh. Installs Python dependencies once
# the uv project exists (M0). A failure is reported but never blocks the session.
[ -f pyproject.toml ] || exit 0
command -v uv >/dev/null || { echo "session-start.local: uv not found"; exit 0; }
uv sync --quiet || echo "session-start.local: uv sync failed"
