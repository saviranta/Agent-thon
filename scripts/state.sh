#!/bin/bash
# state.sh — runtime state, Foreman lock and checkpoints for an Agent-thon project
#
# Usage:
#   state.sh <project> get [dotted.key]
#   state.sh <project> set <dotted.key> <json-or-string>
#   state.sh <project> lock acquire <pid>     # fails if a live Foreman holds the lock (here or on another machine)
#   state.sh <project> lock release [--force] # --force also removes another machine's lock (only if it's really dead)
#   state.sh <project> lock status
#   state.sh <project> checkpoint [label]     # snapshot state.json
#   state.sh <project> pause "<reason>"       # record a clean pause (e.g. usage limit)
#   state.sh <project> unpause
#
# Lock: runtime/foreman.lock (this machine, PID-checked) + branch `foreman-lock` in the agent home's
# GitHub repo when it has one (other machines). Offline → local lock only, with a warning.

set -euo pipefail
source "$(dirname "$0")/lib.sh"

H="$(resolve_project "${1:-}")"
CMD="${2:-}"
RT="$H/runtime"
STATE="$RT/state.json"
LOCK="$RT/foreman.lock"
LOCK_REF="refs/heads/foreman-lock"
HOST="$(hostname -s 2>/dev/null || hostname)"

mkdir -p "$RT/checkpoints"
[[ -f "$STATE" ]] || cp "$TEMPLATES_DIR/home/state.json" "$STATE"

touch_state() {
  json_set "$STATE" updated_at "\"$(now_utc)\""
}

has_remote() { git -C "$H" remote get-url origin >/dev/null 2>&1; }

# Prints the remote lock holder line ("host user pid started_at") or nothing. Exit 2 if the remote is unreachable.
remote_holder() {
  local out
  out="$(git -C "$H" ls-remote origin "$LOCK_REF" 2>/dev/null)" || return 2
  [[ -n "$out" ]] || return 0
  git -C "$H" fetch -q origin "+$LOCK_REF:refs/agentthon/foreman-lock" 2>/dev/null || return 2
  git -C "$H" log -1 --format=%B refs/agentthon/foreman-lock
}

remote_take() {  # $1 = pid, $2 = force (yes|no)
  local tree sha
  tree="$(git -C "$H" hash-object -t tree -w /dev/null)"
  sha="$(git -C "$H" commit-tree "$tree" -m "$HOST $USER $1 $(now_utc)")"
  if [[ "$2" == "yes" ]]; then
    git -C "$H" push -q --force origin "$sha:$LOCK_REF"
  else
    git -C "$H" push -q origin "$sha:$LOCK_REF"
  fi
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
            die "A Foreman is already running on this machine (pid $OLD_PID, since $(json_get "$LOCK" started_at))"
          fi
          echo "Taking over stale local lock (pid $OLD_PID no longer running)"
        fi
        if has_remote; then
          set +e; HOLDER="$(remote_holder)"; RC=$?; set -e
          if [[ $RC -eq 2 ]]; then
            echo "WARNING: agent home repo unreachable — only the local lock is taken. Make sure nobody else runs the Foreman."
          elif [[ -n "$HOLDER" ]]; then
            read -r H_HOST H_USER H_PID H_TS <<< "$HOLDER"
            if [[ "$H_HOST" == "$HOST" && "$H_USER" == "$USER" ]]; then
              echo "Taking over this machine's stale remote lock (pid $H_PID)"
              remote_take "$PID" yes || die "Could not update the remote lock"
            else
              die "A Foreman is running on $H_HOST ($H_USER, since $H_TS). If it is really gone: state.sh <project> lock release --force"
            fi
          else
            remote_take "$PID" no || die "Could not take the remote lock (someone may have started a Foreman just now)"
          fi
        fi
        printf '{\n  "pid": %s,\n  "started_at": "%s",\n  "user": "%s",\n  "host": "%s"\n}\n' "$PID" "$(now_utc)" "$USER" "$HOST" > "$LOCK"
        ;;
      release)
        rm -f "$LOCK"
        if has_remote; then
          set +e; HOLDER="$(remote_holder)"; RC=$?; set -e
          if [[ $RC -eq 0 && -n "$HOLDER" ]]; then
            read -r H_HOST H_USER _ _ <<< "$HOLDER"
            if [[ "$H_HOST" == "$HOST" && "$H_USER" == "$USER" ]] || [[ "${4:-}" == "--force" ]]; then
              git -C "$H" push -q origin --delete foreman-lock 2>/dev/null || echo "WARNING: could not remove the remote lock"
            else
              echo "Remote lock is held by $H_HOST ($H_USER) — left in place (use --force if that Foreman is gone)"
            fi
          fi
        fi
        ;;
      status)
        if [[ -f "$LOCK" ]]; then
          OLD_PID="$(json_get "$LOCK" pid)"
          if kill -0 "$OLD_PID" 2>/dev/null; then echo -n "LOCKED here (pid $OLD_PID)"; else echo -n "STALE here (pid $OLD_PID)"; fi
        else
          echo -n "FREE here"
        fi
        if has_remote; then
          set +e; HOLDER="$(remote_holder)"; RC=$?; set -e
          if [[ $RC -eq 2 ]]; then echo " · remote: unreachable"
          elif [[ -n "$HOLDER" ]]; then echo " · remote: held by $HOLDER"
          else echo " · remote: free"; fi
        else
          echo ""
        fi
        ;;
      *) die "Usage: state.sh <project> lock acquire <pid>|release [--force]|status" ;;
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
