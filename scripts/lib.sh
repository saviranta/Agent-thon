#!/bin/bash
# lib.sh — shared helpers for Agent-thon scripts. Source, don't execute.
#
# A project has two folders side by side:
#   <repo>/          the product repository — product code only, nothing from Agent-thon
#   <repo>-agents/   the agent home ("sidecar") — config, plan, artifacts, contracts source, runtime
# Scripts take either path as <project> and work out the other.

TOOLKIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_FOLDER="${AGENTTHON_BASE:-$(dirname "$TOOLKIT_ROOT")}"
PROJECTS_DIR="$CLAUDE_FOLDER/ClaudeProjects"
TEMPLATES_DIR="$TOOLKIT_ROOT/templates"
AGENTS_DIR="$TOOLKIT_ROOT/agents"
HOME_SUFFIX="-agents"

die() {
  echo "Error: $*" >&2
  exit 1
}

is_agent_home() {
  [[ -f "$1/config.json" ]] && grep -q '"agentthon_home": *true' "$1/config.json"
}

# Resolve <project> (agent home or product repo) to the agent home. Must be inside ClaudeFolder.
# Usage: HOME_DIR=$(resolve_project "<path>") || exit 1
resolve_project() {
  local path="${1:-.}"
  path="${path/#\~/$HOME}"
  [[ -d "$path" ]] || die "Directory not found: $path"
  local real
  real="$(cd "$path" && pwd -P)"
  [[ "$real" == "$CLAUDE_FOLDER"/* ]] || die "Project must be inside $CLAUDE_FOLDER"
  if is_agent_home "$real"; then
    echo "$real"
  elif is_agent_home "$real$HOME_SUFFIX"; then
    echo "$real$HOME_SUFFIX"
  elif [[ -d "$real/.agentthon" ]]; then
    die "$real uses the old in-repo layout (.agentthon/ inside the repo). Migrate it to an agent home first."
  else
    die "Not an Agent-thon project: $real (no ${real##*/}$HOME_SUFFIX/ next to it). Run agentthon-init.sh first."
  fi
}

# Product repo path for an agent home: runtime/local.json repo_path (machine-local override),
# else config.repo_path (relative to the home), else a sibling folder whose origin is config.git.github_repo.
repo_of() {
  local rel="" gh d
  [[ -f "$1/runtime/local.json" ]] && rel="$(json_get "$1/runtime/local.json" repo_path)"
  [[ -n "$rel" ]] || rel="$(json_get "$1/config.json" repo_path)"
  if [[ -n "$rel" ]] && (cd "$1" && cd "$rel" 2>/dev/null); then
    (cd "$1" && cd "$rel" && pwd -P)
    return
  fi
  gh="$(json_get "$1/config.json" git.github_repo)"
  if [[ -n "$gh" ]]; then
    for d in "$(dirname "$1")"/*/; do
      d="${d%/}"
      [[ "$d" == "$1" ]] && continue
      if git -C "$d" remote get-url origin 2>/dev/null | grep -qE "github.com[:/]$gh(\.git)?$"; then
        (cd "$d" && pwd -P)
        return
      fi
    done
  fi
  die "Product repo not found for $1 (config.repo_path '$rel'). Clone it next to the agent home, or set it: json in $1/runtime/local.json {\"repo_path\": \"../<folder>\"}"
}

# Read a value from a JSON file by dotted key. Prints nothing if missing.
# Usage: json_get <file> <dotted.key>
json_get() {
  JG_FILE="$1" JG_KEY="$2" python3 -c '
import json, os
d = json.load(open(os.environ["JG_FILE"]))
for k in os.environ["JG_KEY"].split("."):
    if isinstance(d, dict) and k in d:
        d = d[k]
    else:
        raise SystemExit(0)
print(json.dumps(d) if isinstance(d, (dict, list)) else ("" if d is None else d))
'
}

# Set a value in a JSON file by dotted key. Value is parsed as JSON, falling back to string.
# Usage: json_set <file> <dotted.key> <value>
json_set() {
  JS_FILE="$1" JS_KEY="$2" JS_VAL="$3" python3 -c '
import json, os
path = os.environ["JS_FILE"]
d = json.load(open(path))
raw = os.environ["JS_VAL"]
try:
    val = json.loads(raw)
except ValueError:
    val = raw
keys = os.environ["JS_KEY"].split(".")
cur = d
for k in keys[:-1]:
    cur = cur.setdefault(k, {})
cur[keys[-1]] = val
tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump(d, f, indent=2)
    f.write("\n")
os.replace(tmp, path)
'
}

now_utc() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

# Active profile: machine-local override (runtime/local.json) wins over the shared default in config.json.
# Usage: active_profile <agent_home>
active_profile() {
  local local_file="$1/runtime/local.json" p=""
  [[ -f "$local_file" ]] && p="$(json_get "$local_file" profile)"
  [[ -n "$p" ]] || p="$(json_get "$1/config.json" profile)"
  echo "$p"
}
