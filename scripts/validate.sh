#!/bin/bash
# validate.sh — check that a project is correctly set up for Agent-thon
#
# Usage: validate.sh <project-path>

set -uo pipefail
source "$(dirname "$0")/lib.sh"

PROJECT_ROOT="$(resolve_project "${1:-}")" || exit 1
A="$PROJECT_ROOT/.agentthon"
FAIL=0

check() {
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "PASS  $label"; else echo "FAIL  $label"; FAIL=1; fi
}
warn() {
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "PASS  $label"; else echo "WARN  $label"; fi
}
valid_json() { python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$1"; }
profile_ok() {
  local p; p="$(active_profile "$PROJECT_ROOT")"
  [[ -n "$(json_get "$A/config.json" "profiles.$p.models")" ]]
}
runtime_ignored() { git -C "$PROJECT_ROOT" check-ignore -q .agentthon/runtime/state.json; }
env_ignored() { git -C "$PROJECT_ROOT" check-ignore -q .env; }
checks_filled() {
  python3 -c 'import json,sys; c=json.load(open(sys.argv[1]))["checks"]; sys.exit(0 if any(c.get(k) for k in ("lint","types","unit")) else 1)' "$A/config.json"
}

echo "Validating $PROJECT_ROOT"
echo ""
check "config.json is valid JSON"            valid_json "$A/config.json"
check "active profile is defined"            profile_ok
check "runtime/state.json is valid JSON"     valid_json "$A/runtime/state.json"
check "ownership.yml exists"                 test -f "$A/ownership.yml"
check "claims.md exists"                     test -f "$A/claims.md"
check ".claude/settings.json is valid JSON"  valid_json "$PROJECT_ROOT/.claude/settings.json"
check "git repository"                       git -C "$PROJECT_ROOT" rev-parse --git-dir
check ".agentthon/runtime/ is gitignored"    runtime_ignored
check ".env is gitignored"                   env_ignored
warn  "GitHub remote configured"             git -C "$PROJECT_ROOT" remote get-url origin
warn  "project checks filled (by Architect)" checks_filled
warn  "brief.md written (Architect session 0)" test -f "$A/artifacts/brief.md"
echo ""
echo "Foreman lock: $(bash "$TOOLKIT_ROOT/scripts/state.sh" "$PROJECT_ROOT" lock status)"
echo "Profile:      $(active_profile "$PROJECT_ROOT") (shared default: $(json_get "$A/config.json" profile))"
exit $FAIL
