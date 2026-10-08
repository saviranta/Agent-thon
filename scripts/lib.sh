#!/bin/bash
# lib.sh — shared helpers for Agent-thon scripts. Source, don't execute.

TOOLKIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_FOLDER="${AGENTTHON_BASE:-$(dirname "$TOOLKIT_ROOT")}"
PROJECTS_DIR="$CLAUDE_FOLDER/ClaudeProjects"
TEMPLATES_DIR="$TOOLKIT_ROOT/templates"
AGENTS_DIR="$TOOLKIT_ROOT/agents"

die() {
  echo "Error: $*" >&2
  exit 1
}

# Resolve a project path and verify it is inside ClaudeFolder and initialised.
# Usage: PROJECT_ROOT=$(resolve_project "<path>") || exit 1
resolve_project() {
  local path="${1:-.}"
  path="${path/#\~/$HOME}"
  [[ -d "$path" ]] || die "Directory not found: $path"
  local real
  real="$(cd "$path" && pwd -P)"
  [[ "$real" == "$CLAUDE_FOLDER"/* ]] || die "Project must be inside $CLAUDE_FOLDER"
  [[ -d "$real/.agentthon" ]] || die "Not an Agent-thon project (no .agentthon/): $real. Run agentthon-init.sh first."
  echo "$real"
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

# Active profile: machine-local override (.agentthon/runtime/local.json) wins over the shared default in config.json.
# Usage: active_profile <project_root>
active_profile() {
  local local_file="$1/.agentthon/runtime/local.json" p=""
  [[ -f "$local_file" ]] && p="$(json_get "$local_file" profile)"
  [[ -n "$p" ]] || p="$(json_get "$1/.agentthon/config.json" profile)"
  echo "$p"
}
