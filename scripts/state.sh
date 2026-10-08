#!/bin/bash
# state.sh — runtime state, Foreman lock and checkpoints for an Agent-thon project
#
# Usage:
#   state.sh <project> get [dotted.key]
#   state.sh <project> set <dotted.key> <json-or-string>
#   state.sh <project> lock acquire <pid>     # fails if a live Foreman holds the lock
#   state.sh <project> lock release
#   state.sh <project> lock status
#   state.sh <project> checkpoint [label]     # snapshot state.json
#   state.sh <project> pause "<reason>"       # record a clean pause (e.g. usage limit)
#   state.sh <project> unpause

set -euo pipefail
source "$(dirname "$0")/lib.sh"

PROJECT_ROOT="$(resolve_project "${1:-}")"
CMD="${2:-}"
RT="$PROJECT_ROOT/.agentthon/runtime"
STATE="$RT/state.json"
LOCK="$RT/foreman.lock"

[[ -f "$STATE" ]] || cp "$TEMPLATES_DIR/project/state.json" "$STATE"

touch_state() {
  json_set "$STATE" updated_at "\"$(now_utc)\""
}

case "$CMD" in
  get)
    if [[ -n "${3:-}" ]]; then json_get "$STATE" "$3"; else cat "$STATE"; fi
    ;;
  set)
    [[ -n "${3:-}" && $# -ge 4 ]] || die "Usage: state.sh <project> set <key> <value>"
    json_set "$STATE" "$3" "$4"
    touch_state
    ;;
  lock)
    case "${3:-}" in
      acquire)
        PID="${4:-}"
        [[ "$PID" =~ ^[0-9]+$ ]] || die "Usage: state.sh <project> lock acquire <pid>"
        if [[ -f "$LOCK" ]]; then
          OLD_PID="$(json_get "$LOCK" pid)"
          if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
            die "A Foreman is already running on this project (pid $OLD_PID, since $(json_get "$LOCK" started_at))"
          fi
          echo "Taking over stale lock (pid $OLD_PID no longer running)"
        fi
        printf '{\n  "pid": %s,\n  "started_at": "%s",\n  "user": "%s"\n}\n' "$PID" "$(now_utc)" "$USER" > "$LOCK"
        ;;
      release)
        rm -f "$LOCK"
        ;;
      status)
        if [[ -f "$LOCK" ]]; then
          OLD_PID="$(json_get "$LOCK" pid)"
          if kill -0 "$OLD_PID" 2>/dev/null; then echo "LOCKED (pid $OLD_PID)"; else echo "STALE (pid $OLD_PID)"; fi
        else
          echo "FREE"
        fi
        ;;
      *) die "Usage: state.sh <project> lock acquire <pid>|release|status" ;;
    esac
    ;;
  checkpoint)
    LABEL="${3:-auto}"
    LABEL="${LABEL//[^A-Za-z0-9._-]/-}"
    DEST="$RT/checkpoints/$(date -u +%Y%m%dT%H%M%SZ)-$LABEL.json"
    cp "$STATE" "$DEST"
    # keep the 50 most recent
    ls -1t "$RT/checkpoints"/*.json 2>/dev/null | tail -n +51 | while read -r f; do rm -f "$f"; done
    echo "$DEST"
    ;;
  pause)
    REASON="${3:-unspecified}"
    PAUSE_REASON="$REASON" PAUSE_TS="$(now_utc)" STATE_FILE="$STATE" python3 -c '
import json, os
p = os.environ["STATE_FILE"]
d = json.load(open(p))
d["paused"] = {"reason": os.environ["PAUSE_REASON"], "at": os.environ["PAUSE_TS"]}
d["updated_at"] = os.environ["PAUSE_TS"]
json.dump(d, open(p, "w"), indent=2)
'
    ;;
  unpause)
    json_set "$STATE" paused null
    touch_state
    ;;
  *)
    die "Usage: state.sh <project> get|set|lock|checkpoint|pause|unpause ..."
    ;;
esac
