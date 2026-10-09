#!/bin/bash
# gate.sh — deterministic quality gate: project checks + exact versions (+ ownership in task mode). No LLM.
#
# Usage:
#   gate.sh <project> <work-dir> [--task <ids|@agents> --base <ref>] [--results <dir>] [--only <categories>]
#
#   <project>    agent home (or the product repo next to it)
#   <work-dir>   a product worktree (task, fix or the Foreman's wave worktree) or a checkout
#   --task/--base  also run the ownership check for that task against <ref>
#   --results    write gate.json + per-check logs there (default: <home>/runtime/gate-results)
#   --only       comma-separated subset of: setup,lint,types,unit,contract,e2e,versions
#                (default: setup,lint,types,unit,contract,versions)
#
# Check commands come from config.checks.<category> of the released plan (runtime/plan, else the agent
# home) and run from <work-dir>. `versions` is built in (exact dependency versions, no ^ or ~).
# Exit 0 = all passed, 1 = something failed, 2 = usage / no checks configured.

set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPTS/lib.sh"

H="$(resolve_project "${1:-}")" || exit 2
WORK_DIR="${2:-}"
[[ -d "$WORK_DIR" ]] || { echo "Usage: gate.sh <project> <work-dir> [--task ids --base ref] [--results dir] [--only cats]" >&2; exit 2; }
WORK_DIR="$(cd "$WORK_DIR" && pwd)"
shift 2
TASK="" BASE="" RESULTS="" ONLY="setup,lint,types,unit,contract,versions"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task) TASK="$2"; shift 2 ;;
    --base) BASE="$2"; shift 2 ;;
    --results) RESULTS="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
RESULTS="${RESULTS:-$H/runtime/gate-results}"
mkdir -p "$RESULTS"
PLAN="$H"
[[ -f "$H/runtime/plan/config.json" ]] && PLAN="$H/runtime/plan"
CONFIG="$PLAN/config.json"

# Emit "category<TAB>command" lines for the selected categories (versions = built in).
COMMANDS="$(GATE_CONFIG="$CONFIG" GATE_ONLY="$ONLY" GATE_SCRIPTS="$SCRIPTS" python3 -c '
import json, os
checks = json.load(open(os.environ["GATE_CONFIG"])).get("checks", {})
scripts = os.environ["GATE_SCRIPTS"]
for cat in os.environ["GATE_ONLY"].split(","):
    if cat == "versions":
        print(f"versions\tpython3 {scripts}/check-versions.py .")
        continue
    for cmd in checks.get(cat, []) or []:
        print(f"{cat}\t{cmd}")
')"

if ! grep -qv $'^versions\t' <<< "$COMMANDS" && [[ -z "$TASK" ]]; then
  echo "gate: no project checks configured for [$ONLY] — the Architect must fill config.checks"
  exit 2
fi

OVERALL=0
SUMMARY="[]"
i=0
add_result() {  # category command status log
  SUMMARY="$(S="$SUMMARY" C="$1" CMD="$2" ST="$3" L="$4" python3 -c '
import json, os
s = json.loads(os.environ["S"])
s.append({"category": os.environ["C"], "command": os.environ["CMD"], "status": os.environ["ST"], "log": os.environ["L"]})
print(json.dumps(s))')"
}

while IFS=$'\t' read -r CAT CMD; do
  [[ -z "$CAT" ]] && continue
  i=$((i + 1))
  LOG="$RESULTS/$(printf '%02d' $i)-$CAT.log"
  if (cd "$WORK_DIR" && bash -c "$CMD") >"$LOG" 2>&1; then
    echo "PASS  $CAT: $CMD"
    add_result "$CAT" "$CMD" pass "$LOG"
  else
    echo "FAIL  $CAT: $CMD   (log: $LOG)"
    tail -n 25 "$LOG" | sed 's/^/      /'
    add_result "$CAT" "$CMD" fail "$LOG"
    OVERALL=1
    [[ "$CAT" == "setup" ]] && break   # nothing else can run without setup
  fi
done <<< "$COMMANDS"

if [[ -n "$TASK" ]]; then
  [[ -n "$BASE" ]] || { echo "--task requires --base" >&2; exit 2; }
  LOG="$RESULTS/ownership.log"
  if python3 "$SCRIPTS/ownership-check.py" "$H" "$WORK_DIR" "$TASK" "$BASE" >"$LOG" 2>&1; then
    echo "PASS  ownership"
    add_result ownership "ownership-check $TASK" pass "$LOG"
  else
    echo "FAIL  ownership   (log: $LOG)"
    sed 's/^/      /' "$LOG"
    add_result ownership "ownership-check $TASK" fail "$LOG"
    OVERALL=1
  fi
fi

S="$SUMMARY" OUT="$RESULTS/gate.json" PASSED="$OVERALL" TASK_ID="$TASK" python3 -c '
import json, os, datetime
json.dump({"task": os.environ["TASK_ID"] or None,
           "verdict": "PASS" if os.environ["PASSED"] == "0" else "FAIL",
           "at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "checks": json.loads(os.environ["S"])}, open(os.environ["OUT"], "w"), indent=2)'
echo "gate: $([[ $OVERALL -eq 0 ]] && echo PASS || echo FAIL)  ($RESULTS/gate.json)"
exit $OVERALL
