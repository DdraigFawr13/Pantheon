#!/usr/bin/env bash
# Keep the save on the `saves` branch as one text file, pantheon.sql (D-041). Cloud containers are wiped,
# so `push` runs after every committed turn. `pull` loads the branch's save; an existing local save is
# moved aside as a .bak first, never overwritten (GAME-05). Never touches the working branch.
set -euo pipefail
cd "$(dirname "$0")/.."
DUMP=data/pantheon.sql
mkdir -p data

fetch() {
  for wait in 2 4 8 16; do
    git fetch -q origin saves 2>/dev/null && return 0
    git ls-remote --exit-code --heads origin saves >/dev/null 2>&1 || return 1  # No saves branch yet.
    sleep "$wait"
  done
  return 1
}

case "${1:-}" in
  pull)
    if ! fetch; then
      echo "No saves branch yet: a new game starts here."
      exit 0
    fi
    git show origin/saves:pantheon.sql > "$DUMP"
    uv run -q pantheon session import "$DUMP"
    ;;
  push)
    uv run -q pantheon session export "$DUMP"
    fetch || true
    blob=$(git hash-object -w "$DUMP")
    tree=$(printf '100644 blob %s\tpantheon.sql\n' "$blob" | git mktree)
    parent=$(git rev-parse -q --verify refs/remotes/origin/saves || true)
    if [ -n "$parent" ] && [ "$(git rev-parse "$parent^{tree}")" = "$tree" ]; then
      echo "Save unchanged."
      exit 0
    fi
    commit=$(git commit-tree "$tree" ${parent:+-p "$parent"} -m "save: $(date -u +%Y-%m-%dT%H:%MZ)")
    for wait in 2 4 8 16 0; do
      if git push -q origin "$commit:refs/heads/saves"; then
        git update-ref refs/remotes/origin/saves "$commit"
        echo "Saved to the saves branch."
        exit 0
      fi
      [ "$wait" = 0 ] || sleep "$wait"
    done
    echo "Push failed: the save is still in data/pantheon.db and $DUMP." >&2
    exit 1
    ;;
  *)
    echo "usage: scripts/saves.sh pull|push" >&2
    exit 2
    ;;
esac
