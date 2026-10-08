#!/bin/bash
# profile.sh — show or switch the active profile, or resolve a setting from it
#
# Usage:
#   profile.sh <project>                 # show active profile and its settings
#   profile.sh <project> set pro|max     # switch on this machine only (Foreman picks it up at the next wave)
#   profile.sh <project> default pro|max # change the shared default in config.json (commit via PR)
#   profile.sh <project> model <role>    # interactive|foreman|workers|reviewers|debug_deep|status
#   profile.sh <project> get <key>       # e.g. parallel_workers, review_mode, fix_attempts.critical

set -euo pipefail
source "$(dirname "$0")/lib.sh"

PROJECT_ROOT="$(resolve_project "${1:-}")"
CONFIG="$PROJECT_ROOT/.agentthon/config.json"
ACTIVE="$(active_profile "$PROJECT_ROOT")"
LOCAL="$PROJECT_ROOT/.agentthon/runtime/local.json"

require_profile() {
  [[ -n "$(json_get "$CONFIG" "profiles.$1")" ]] || die "Unknown profile: '$1' (defined: $(json_get "$CONFIG" profiles | python3 -c 'import json,sys; print(", ".join(json.load(sys.stdin)))'))"
}

case "${2:-}" in
  "")
    echo "Active profile: $ACTIVE"
    json_get "$CONFIG" "profiles.$ACTIVE" | python3 -m json.tool
    ;;
  set)
    require_profile "${3:-}"
    [[ -f "$LOCAL" ]] || echo '{}' > "$LOCAL"
    json_set "$LOCAL" profile "\"$3\""
    echo "Profile set to $3 on this machine (the Foreman applies it from the next wave or on resume)"
    ;;
  default)
    require_profile "${3:-}"
    json_set "$CONFIG" profile "\"$3\""
    echo "Shared default profile set to $3 in config.json — commit it via a PR"
    ;;
  model)
    VAL="$(json_get "$CONFIG" "profiles.$ACTIVE.models.${3:-}")"
    [[ -n "$VAL" ]] || die "No model for role '${3:-}' in profile $ACTIVE"
    echo "$VAL"
    ;;
  get)
    VAL="$(json_get "$CONFIG" "profiles.$ACTIVE.${3:-}")"
    [[ -n "$VAL" ]] || die "No setting '${3:-}' in profile $ACTIVE"
    echo "$VAL"
    ;;
  *)
    die "Usage: profile.sh <project> [set <name> | model <role> | get <key>]"
    ;;
esac
