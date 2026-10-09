#!/bin/bash
# setup-toolkit.sh — one-time: create the toolkit's own Python environment (Agent-thon/.venv, not committed)
# with the packages its scripts use (jsonschema for contract example validation). Exact versions.
#
# Usage: setup-toolkit.sh

set -euo pipefail
source "$(dirname "$0")/lib.sh"

VENV="$TOOLKIT_ROOT/.venv"
[[ -x "$VENV/bin/python" ]] || python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --disable-pip-version-check "jsonschema==4.23.0" "PyYAML==6.0.2"
echo "Toolkit environment ready: $VENV"
