#!/bin/bash
# agentthon-init.sh — set up a project for Agent-thon (non-interactive; the agentthon-init skill calls this)
#
# Usage:
#   agentthon-init.sh new   <name> "<description>"   # new product repo ClaudeProjects/<name> + agent home <name>-agents
#   agentthon-init.sh adopt <repo-path> "<description>"  # existing product repo; creates <repo>-agents next to it
#
# The product repo never gets Agent-thon files. Everything the agents need lives in the agent home,
# which is its own git repository (share it via github-setup.sh).

set -euo pipefail
source "$(dirname "$0")/lib.sh"

MODE="${1:-}"
TARGET="${2:-}"
DESC="${3:-}"

[[ "$MODE" == "new" || "$MODE" == "adopt" ]] && [[ -n "$TARGET" ]] || {
  echo "Usage: agentthon-init.sh new <name> \"<description>\" | adopt <repo-path> \"<description>\"" >&2
  exit 1
}

if [[ "$MODE" == "new" ]]; then
  [[ "$TARGET" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die "Project name may contain letters, digits, '.', '_' and '-' only"
  REPO="$PROJECTS_DIR/$TARGET"
  [[ -e "$REPO" ]] && die "Already exists: $REPO (use adopt)"
else
  TARGET="${TARGET/#\~/$HOME}"
  [[ -d "$TARGET" ]] || die "Directory not found: $TARGET"
  REPO="$(cd "$TARGET" && pwd -P)"
  [[ "$REPO" == "$CLAUDE_FOLDER"/* ]] || die "Project must be inside $CLAUDE_FOLDER"
  git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || die "$REPO is not a git repository"
  [[ -d "$REPO/.agentthon" ]] && die "$REPO has an old in-repo .agentthon/ — migrate it instead"
fi

NAME="$(basename "$REPO")"
H="$REPO$HOME_SUFFIX"
[[ -e "$H" ]] && die "Agent home already exists: $H"
T="$TEMPLATES_DIR/home"

echo "Product repo: $REPO ($MODE)"
echo "Agent home:   $H"

# ─── product repo (new projects only; adopted repos are not touched) ───
if [[ "$MODE" == "new" ]]; then
  mkdir -p "$REPO"
  sed -e "s|<name>|$NAME|" -e "s|<description>|$DESC|" "$TEMPLATES_DIR/repo/README.md" > "$REPO/README.md"
  cp "$TEMPLATES_DIR/repo/gitignore" "$REPO/.gitignore"
  git -C "$REPO" init -b main -q
  git -C "$REPO" add -A
  git -C "$REPO" commit -q -m "Initial commit"
  echo "  product repo created (README.md, .gitignore)"
fi

# ─── agent home ───
mkdir -p "$H"/artifacts/{context,ui} "$H"/contracts/examples "$H"/waves "$H"/evals "$H"/runtime/{checkpoints,results,worktrees}

GH_REPO="$(git -C "$REPO" remote get-url origin 2>/dev/null | sed -E 's#^(git@github.com:|https://github.com/)##; s#\.git$##' || true)"
MAIN="$(git -C "$REPO" symbolic-ref --short HEAD 2>/dev/null || echo main)"

INIT_T="$T/config.json" INIT_OUT="$H/config.json" INIT_NAME="$NAME" INIT_DESC="$DESC" \
INIT_TS="$(now_utc)" INIT_GH="$GH_REPO" INIT_MAIN="$MAIN" python3 -c '
import json, os
e = os.environ
c = json.load(open(e["INIT_T"]))
c.update(project_name=e["INIT_NAME"], project_description=e["INIT_DESC"],
         repo_path="../" + e["INIT_NAME"], created_at=e["INIT_TS"])
c["git"]["github_repo"] = e["INIT_GH"]
c["git"]["main_branch"] = e["INIT_MAIN"] or "main"
with open(e["INIT_OUT"], "w") as f:
    json.dump(c, f, indent=2); f.write("\n")
'
cp "$T/state.json" "$H/runtime/state.json"
cp "$T/ownership.yml" "$H/ownership.yml"
cp "$T/claims.md" "$H/claims.md"
cp "$T/TEAM.md" "$H/TEAM.md"
cp "$T/gitignore" "$H/.gitignore"
: > "$H/requests.md"
: > "$H/contracts/examples/.gitkeep"
printf '# Eval decisions\n\n| Wave | Decision | Who | Follow-up tasks | Date |\n|---|---|---|---|---|\n' > "$H/evals/decisions.md"
printf '# %s — agent home\n\nAgent-thon plan and artifacts for the product repo `%s` (cloned next to this folder).\nSee TEAM.md for how we work.\n' "$NAME" "$NAME" > "$H/README.md"

git -C "$H" init -b main -q
git -C "$H" add -A
git -C "$H" commit -q -m "Initialise Agent-thon agent home for $NAME"
echo "  agent home created and committed"

echo ""
echo "Done. Next:"
echo "  bash $TOOLKIT_ROOT/scripts/validate.sh $H"
[[ -z "$GH_REPO" ]] && echo "  create the product repo on GitHub and add it as origin of $REPO"
echo "  bash $TOOLKIT_ROOT/scripts/github-setup.sh $H     # private GitHub repo for the agent home + labels"
echo "  bash $TOOLKIT_ROOT/scripts/run-agent.sh architect $H"
