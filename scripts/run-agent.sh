#!/bin/bash
# run-agent.sh — start an Agent-thon agent in a Claude Code session scoped to one project
#
# Usage:
#   run-agent.sh <agent> <project-path> [first-message]
#
# Examples:
#   run-agent.sh architect  ~/ClaudeFolder/ClaudeProjects/my-app
#   run-agent.sh prototyper ~/ClaudeFolder/ClaudeProjects/my-app
#   run-agent.sh foreman    ~/ClaudeFolder/ClaudeProjects/my-app resume
#
# The model comes from the project's active profile (.agentthon/config.json).

set -euo pipefail
source "$(dirname "$0")/lib.sh"

AGENT="${1:-}"
list_agents() {
  for f in "$AGENTS_DIR"/*/AGENT.md; do [[ -f "$f" ]] && echo "  $(basename "$(dirname "$f")")"; done
}

if [[ -z "$AGENT" || -z "${2:-}" ]]; then
  echo "Usage: run-agent.sh <agent> <project-path> [first-message]" >&2
  echo "Agents:" >&2; list_agents >&2
  exit 1
fi

PROJECT_ROOT="$(resolve_project "$2")"
FIRST_MESSAGE="${3:-}"
AGENT_FILE="$AGENTS_DIR/$AGENT/AGENT.md"
[[ -f "$AGENT_FILE" ]] || { echo "Unknown agent: $AGENT. Available:" >&2; list_agents >&2; exit 1; }

case "$AGENT" in
  architect|prototyper) ROLE="interactive" ;;
  foreman)              ROLE="foreman" ;;
  *) die "'$AGENT' is not started directly (workers are dispatched by the Foreman)" ;;
esac

MODEL="$(bash "$TOOLKIT_ROOT/scripts/profile.sh" "$PROJECT_ROOT" model "$ROLE")"
PROFILE="$(active_profile "$PROJECT_ROOT")"

# One Foreman per project: take the lock with this shell's PID, which `exec` hands to claude.
if [[ "$AGENT" == "foreman" ]]; then
  bash "$TOOLKIT_ROOT/scripts/state.sh" "$PROJECT_ROOT" lock acquire $$
fi

export AGENTTHON_TOOLKIT="$TOOLKIT_ROOT"
export AGENTTHON_PROJECT="$PROJECT_ROOT"
export AGENTTHON_AGENT="$AGENT"

echo "Agent:    $AGENT"
echo "Project:  $PROJECT_ROOT"
echo "Profile:  $PROFILE   Model: $MODEL"
echo ""

SYSTEM_PROMPT="$(cat "$AGENT_FILE")

---
Runtime context:
- Toolkit root: $TOOLKIT_ROOT
- Project root: $PROJECT_ROOT
- Active profile at launch: $PROFILE"

cd "$PROJECT_ROOT"
ARGS=(--append-system-prompt "$SYSTEM_PROMPT" --model "$MODEL" --add-dir "$TOOLKIT_ROOT")
if [[ -n "$FIRST_MESSAGE" ]]; then
  exec claude "${ARGS[@]}" "$FIRST_MESSAGE"
else
  exec claude "${ARGS[@]}"
fi
