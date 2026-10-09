#!/bin/bash
# github-setup.sh — share the agent home on GitHub (private repo) and create its labels
#
# Usage: github-setup.sh <project> [owner/name]
#   default name: <product-repo-owner>/<product-repo-name>-agents (owner falls back to your gh user)
#
# - creates the private repo (if the agent home has no origin yet) and pushes main
# - records it in config.git.agents_github_repo (and the product repo in config.git.github_repo)
# - labels in the agent home repo: architect (requests to the Architect), foreman-question (Foreman → Architect)
# The product repo is not changed.

set -euo pipefail
source "$(dirname "$0")/lib.sh"

H="$(resolve_project "${1:-}")"
REPO="$(repo_of "$H")"
CFG="$H/config.json"

PRODUCT_GH="$(json_get "$CFG" git.github_repo)"
if [[ -z "$PRODUCT_GH" ]]; then
  PRODUCT_GH="$(git -C "$REPO" remote get-url origin 2>/dev/null | sed -E 's#^(git@github.com:|https://github.com/)##; s#\.git$##' || true)"
  [[ -n "$PRODUCT_GH" ]] && json_set "$CFG" git.github_repo "\"$PRODUCT_GH\""
fi

if git -C "$H" remote get-url origin >/dev/null 2>&1; then
  AGENTS_GH="$(git -C "$H" remote get-url origin | sed -E 's#^(git@github.com:|https://github.com/)##; s#\.git$##')"
  echo "Agent home already has origin: $AGENTS_GH"
else
  AGENTS_GH="${2:-}"
  if [[ -z "$AGENTS_GH" ]]; then
    OWNER="${PRODUCT_GH%%/*}"
    [[ -n "$OWNER" ]] || OWNER="$(gh api user -q .login)"
    AGENTS_GH="$OWNER/$(basename "$H")"
  fi
  echo "Creating private repo $AGENTS_GH"
  gh repo create "$AGENTS_GH" --private --description "Agent-thon plan and artifacts for ${PRODUCT_GH:-$(basename "$REPO")}" >/dev/null
  git -C "$H" remote add origin "https://github.com/$AGENTS_GH.git"
fi

json_set "$CFG" git.agents_github_repo "\"$AGENTS_GH\""
if [[ -n "$(git -C "$H" status --porcelain config.json)" ]]; then
  git -C "$H" add config.json
  git -C "$H" commit -q -m "Record GitHub repositories"
fi
git -C "$H" push -q -u origin "$(git -C "$H" symbolic-ref --short HEAD)"
echo "Pushed agent home to $AGENTS_GH"

for label in "architect|5319e7|Request or question for the Agent-thon Architect" \
             "foreman-question|d93f0b|Question from the Foreman (parked task, conflict, failed smoke check)"; do
  IFS='|' read -r name color desc <<< "$label"
  if gh label create "$name" -R "$AGENTS_GH" --color "$color" --description "$desc" >/dev/null 2>&1; then
    echo "label created: $name"
  else
    echo "label exists:  $name"
  fi
done

echo ""
echo "Teammates: clone both repos side by side, with these folder names:"
echo "  git clone https://github.com/${PRODUCT_GH:-<owner>/<repo>}.git $(basename "$REPO")"
echo "  git clone https://github.com/$AGENTS_GH.git $(basename "$H")"
echo "Only one person runs the Foreman at a time (it takes a lock in the agent home repo)."
