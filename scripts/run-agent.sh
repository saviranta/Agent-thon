#!/bin/bash
# run-agent.sh — start an Agent-thon agent in a Claude Code session scoped to one project
#
# Usage:
#   run-agent.sh <agent> <project> [first-message]
#
#   <project> = the agent home (<repo>-agents) or the product repo next to it
#
# Examples:
#   run-agent.sh architect  ~/ClaudeFolder/ClaudeProjects/my-app-agents
#   run-agent.sh prototyper ~/ClaudeFolder/ClaudeProjects/my-app
#   run-agent.sh foreman    ~/ClaudeFolder/ClaudeProjects/my-app resume
#
# The session runs in the agent home (so Claude Code never writes into the product repo) with the
# product repo and the toolkit added as extra directories. The model comes from the active profile.

set -euo pipefail
source "$(dirname "$0")/lib.sh"

AGENT="${1:-}"
list_agents() {
  for f in "$AGENTS_DIR"/*/AGENT.md; do [[ -f "$f" ]] && echo "  $(basename "$(dirname "$f")")"; done
}

if [[ -z "$AGENT" || -z "${2:-}" ]]; then
  echo "Usage: run-agent.sh <agent> <project> [first-message]" >&2
  echo "Agents:" >&2; list_agents >&2
  exit 1
fi

H="$(resolve_project "$2")"
REPO="$(repo_of "$H")"
FIRST_MESSAGE="${3:-}"
AGENT_FILE="$AGENTS_DIR/$AGENT/AGENT.md"
[[ -f "$AGENT_FILE" ]] || { echo "Unknown agent: $AGENT. Available:" >&2; list_agents >&2; exit 1; }

case "$AGENT" in
  architect|prototyper) ROLE="interactive" ;;
  foreman)              ROLE="foreman" ;;
  *) die "'$AGENT' is not started directly (workers are dispatched by the Foreman)" ;;
esac

mkdir -p "$H/runtime"
MODEL="$(bash "$TOOLKIT_ROOT/scripts/profile.sh" "$H" model "$ROLE")"
PROFILE="$(active_profile "$H")"

# Per-machine Claude Code settings (absolute paths differ per machine; never committed).
SETTINGS="$H/runtime/claude-settings.json"
S_T="$TEMPLATES_DIR/home/claude-settings.json" S_OUT="$SETTINGS" S_HOME="$H" S_REPO="$REPO" S_TK="$TOOLKIT_ROOT" \
S_USER="$HOME" S_CFG="$H/config.json" python3 -c '
import json, os
e = os.environ
raw = open(e["S_T"]).read()
for ph, val in (("<home_dir>", e["S_HOME"]), ("<repo_dir>", e["S_REPO"]), ("<toolkit_dir>", e["S_TK"]), ("<user_home>", e["S_USER"])):
    raw = raw.replace(ph, val)
s = json.loads(raw)
s.pop("_comment", None)
extra = json.load(open(e["S_CFG"])).get("network", {}).get("allowed_domains", [])
doms = s["sandbox"]["network"]["allowedDomains"]
doms += [d for d in extra if d not in doms]
json.dump(s, open(e["S_OUT"], "w"), indent=2)
'

# Use the Claude subscription login (Pro/Max), not an API key that happens to be in the shell.
# Set AGENTTHON_AUTH=api to keep ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN deliberately.
if [[ "${AGENTTHON_AUTH:-subscription}" != "api" ]]; then
  if [[ -n "${ANTHROPIC_API_KEY:-}${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
    echo "Note: ignoring ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN for this session (subscription login is used; AGENTTHON_AUTH=api to keep them)."
  fi
  unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN
fi

export AGENTTHON_TOOLKIT="$TOOLKIT_ROOT"
export AGENTTHON_HOME="$H"
export AGENTTHON_REPO="$REPO"
export AGENTTHON_AGENT="$AGENT"

echo "Agent:       $AGENT"
echo "Agent home:  $H"
echo "Product repo: $REPO"
echo "Profile:     $PROFILE   Model: $MODEL"
echo ""

SYSTEM_PROMPT="$(cat "$AGENT_FILE")

---
Runtime context:
- Toolkit: $TOOLKIT_ROOT
- Agent home (<home>, your working directory; pass it as <project> to scripts): $H
- Product repo (<repo>): $REPO
- Active profile at launch: $PROFILE"

cd "$H"
ARGS=(--settings "$SETTINGS" --append-system-prompt "$SYSTEM_PROMPT" --model "$MODEL" --add-dir "$REPO" --add-dir "$TOOLKIT_ROOT")
[[ -n "$FIRST_MESSAGE" ]] && ARGS+=("$FIRST_MESSAGE")

if [[ "$AGENT" != "foreman" ]]; then
  exec claude "${ARGS[@]}"
fi

# One Foreman per project, across machines: the lock lives locally and (if shared) in the agent home repo.
bash "$TOOLKIT_ROOT/scripts/state.sh" "$H" lock acquire $$
release() { bash "$TOOLKIT_ROOT/scripts/state.sh" "$H" lock release >/dev/null 2>&1 || true; }
trap release EXIT INT TERM
set +e
claude "${ARGS[@]}"
