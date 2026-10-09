#!/bin/bash
# validate.sh — check that a project is correctly set up for Agent-thon
#
# Usage: validate.sh <project>   (agent home or product repo)

set -uo pipefail
source "$(dirname "$0")/lib.sh"

H="$(resolve_project "${1:-}")" || exit 1
REPO="$(repo_of "$H")" || exit 1
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
  local p; p="$(active_profile "$H")"
  [[ -n "$(json_get "$H/config.json" "profiles.$p.models")" ]]
}
runtime_ignored() { git -C "$H" check-ignore -q runtime/state.json; }
repo_clean_of_agentthon() {
  ! git -C "$REPO" ls-files | grep -qE '^(\.agentthon/|AGENTS\.md$|\.claude/)'
}
checks_filled() {
  python3 -c 'import json,sys; c=json.load(open(sys.argv[1]))["checks"]; sys.exit(0 if any(c.get(k) for k in ("lint","types","unit")) else 1)' "$H/config.json"
}
layout_filled() {
  python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); sys.exit(0 if c.get("layout",{}).get("folders") and c.get("contracts_dir") else 1)' "$H/config.json"
}

echo "Agent home:   $H"
echo "Product repo: $REPO"
echo ""
check "config.json is valid JSON"               valid_json "$H/config.json"
check "active profile is defined"               profile_ok
check "ownership.yml exists"                    test -f "$H/ownership.yml"
check "claims.md exists"                        test -f "$H/claims.md"
check "agent home is a git repository"          git -C "$H" rev-parse --git-dir
check "runtime/ is gitignored in the agent home" runtime_ignored
check "product repo is a git repository"        git -C "$REPO" rev-parse --git-dir
check "product repo has no Agent-thon files"    repo_clean_of_agentthon
warn  "product repo has a GitHub remote"        git -C "$REPO" remote get-url origin
warn  "agent home has a GitHub remote (github-setup.sh)" git -C "$H" remote get-url origin
warn  "brief.md written (Architect session 0)"  test -f "$H/artifacts/brief.md"
warn  "chunks.json written (Architect phase 1)" test -f "$H/chunks.json"
warn  "layout + contracts_dir set (phase 1)"    layout_filled
warn  "project checks filled (phase 2)"         checks_filled
echo ""
echo "Foreman lock: $(bash "$TOOLKIT_ROOT/scripts/state.sh" "$H" lock status)"
echo "Profile:      $(active_profile "$H") (shared default: $(json_get "$H/config.json" profile))"
exit $FAIL
