#!/bin/bash
# protect-main.sh — set up GitHub for an Agent-thon project: branch protection on main + labels
#
# Usage: protect-main.sh <project>
#
# - main: PR required, CI jobs (checks, ownership, hygiene) must pass, 1 approval incl. code owners,
#   admins may bypass (so a solo admin can merge agent PRs opened under their own account).
# - labels: architect (requests to the Architect), agent-review (ask agents to review a human PR)
#
# Note: GitHub Free does not offer branch protection on PRIVATE repositories. If that applies,
# the script says so and still creates the labels; CI + CODEOWNERS still run, merges just aren't enforced.

set -euo pipefail
source "$(dirname "$0")/lib.sh"

PROJECT_ROOT="$(resolve_project "${1:-}")"
cd "$PROJECT_ROOT"
REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)" || die "No GitHub repo for this project (add origin and push first)"
MAIN="$(json_get .agentthon/config.json git.main_branch)"; MAIN="${MAIN:-main}"

echo "Repository: $REPO  (branch: $MAIN)"

for label in "architect|5319e7|Request or question for the Agent-thon Architect" \
             "agent-review|0e8a16|Ask Agent-thon reviewers to review this human PR"; do
  IFS='|' read -r name color desc <<< "$label"
  if gh label create "$name" --color "$color" --description "$desc" >/dev/null 2>&1; then
    echo "label created: $name"
  else
    echo "label exists:  $name"
  fi
done

PAYLOAD='{
  "required_status_checks": { "strict": false, "contexts": ["checks", "ownership", "hygiene"] },
  "enforce_admins": false,
  "required_pull_request_reviews": { "require_code_owner_reviews": true, "required_approving_review_count": 1, "dismiss_stale_reviews": false },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}'
if OUT="$(echo "$PAYLOAD" | gh api -X PUT "repos/$REPO/branches/$MAIN/protection" --input - 2>&1)"; then
  echo "branch protection set on $MAIN (admins can bypass)"
else
  echo "Could not set branch protection:"
  echo "$OUT" | head -5
  if echo "$OUT" | grep -qiE "upgrade|403|not available"; then
    echo ""
    echo "Likely cause: branch protection on private repos needs GitHub Pro/Team."
    echo "Options: make the repo public, upgrade, or continue without enforcement (CI and CODEOWNERS still run)."
  fi
  exit 1
fi
