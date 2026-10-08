#!/bin/bash
# update-tools.sh — copy the scripts CI needs into <project>/.agentthon/bin/ (CI can't see the toolkit)
#
# Usage: update-tools.sh <project>
# Commit the result via a PR (the Architect does this in a plan PR).

set -euo pipefail
source "$(dirname "$0")/lib.sh"

PROJECT_ROOT="$(resolve_project "${1:-}")"
BIN="$PROJECT_ROOT/.agentthon/bin"
mkdir -p "$BIN"
for f in gate.sh ownership.py ownership-check.py check-versions.py sync-instructions.py gen-codeowners.py; do
  cp "$TOOLKIT_ROOT/scripts/$f" "$BIN/$f"
done
chmod +x "$BIN"/*.sh "$BIN"/*.py
VERSION="$(git -C "$TOOLKIT_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "Agent-thon toolkit $VERSION — copied by update-tools.sh; do not edit here." > "$BIN/VERSION"
echo "Updated $BIN (toolkit $VERSION)"
