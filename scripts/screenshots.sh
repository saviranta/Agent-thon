#!/bin/bash
# screenshots.sh — render the app's screens and the frozen prototypes to PNGs for visual comparison. No LLM.
#
# Usage: screenshots.sh <project> <work-dir> <out-dir>
#
# Runs config.design.screenshots (from the released plan) in <work-dir> with:
#   SCREENSHOT_DIR  <out-dir> (created)        — write <screen-id>.app.png and <screen-id>.proto.png there
#   PROTOTYPE_DIR   <plan>/artifacts/ui/prototypes   (prototype pages take ?state=empty|loading|error|populated)
#   SCREENS_JSON    <plan>/artifacts/ui/screens.json (id, route, prototype, states)
# The command itself is product code (a Playwright script set up by the design-system task); it starts the app
# with the fake AI adapter and the hero data, as conventions.md says.
# Exit 0 = screenshots written, 1 = command failed, 2 = usage / not configured.

set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPTS/lib.sh"

H="$(resolve_project "${1:-}")" || exit 2
WORK_DIR="${2:-}" OUT="${3:-}"
[[ -d "$WORK_DIR" && -n "$OUT" ]] || { echo "Usage: screenshots.sh <project> <work-dir> <out-dir>" >&2; exit 2; }
PLAN="$H"
[[ -f "$H/runtime/plan/config.json" ]] && PLAN="$H/runtime/plan"
CMD="$(json_get "$PLAN/config.json" design.screenshots)"
if [[ -z "$CMD" || "$CMD" == "null" ]]; then
  echo "screenshots: config.design.screenshots is not set — the Architect sets it once the design-system task exists"
  exit 2
fi
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
LOG="$OUT/screenshots.log"
if (cd "$WORK_DIR" && SCREENSHOT_DIR="$OUT" PROTOTYPE_DIR="$PLAN/artifacts/ui/prototypes" \
    SCREENS_JSON="$PLAN/artifacts/ui/screens.json" bash -c "$CMD") >"$LOG" 2>&1; then
  echo "screenshots: $(ls "$OUT"/*.png 2>/dev/null | wc -l | tr -d ' ') PNGs in $OUT"
else
  echo "screenshots: FAILED (log: $LOG)"
  tail -n 20 "$LOG" | sed 's/^/      /'
  exit 1
fi
