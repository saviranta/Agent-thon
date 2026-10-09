#!/bin/bash
# smoke.sh — check the deployed app after a merge to main (no LLM)
#
# Usage: smoke.sh <project> [retries] [delay-seconds]
# Reads config.deploy.health_checks: list of URLs, or {"url": ..., "expect": "<substring>"} objects.
# Exit 0 = all healthy (or nothing configured), 1 = a check failed after retries.

set -uo pipefail
source "$(dirname "$0")/lib.sh"

H="$(resolve_project "${1:-}")" || exit 1
RETRIES="${2:-10}"
DELAY="${3:-30}"

CHECKS="$(CFG="$H/config.json" python3 -c '
import json, os
for c in json.load(open(os.environ["CFG"])).get("deploy", {}).get("health_checks", []) or []:
    if isinstance(c, str):
        print(f"{c}\t")
    else:
        print(f"{c[\"url\"]}\t{c.get(\"expect\", \"\")}")
')"
[[ -n "$CHECKS" ]] || { echo "smoke: no health checks configured (config.deploy.health_checks)"; exit 0; }

FAIL=0
while IFS=$'\t' read -r URL EXPECT; do
  ok=0
  for ((i = 1; i <= RETRIES; i++)); do
    BODY="$(curl -fsS --max-time 20 "$URL" 2>/dev/null)" && { [[ -z "$EXPECT" || "$BODY" == *"$EXPECT"* ]]; } && { ok=1; break; }
    sleep "$DELAY"
  done
  if [[ $ok -eq 1 ]]; then echo "PASS  $URL"; else echo "FAIL  $URL (after $RETRIES tries)"; FAIL=1; fi
done <<< "$CHECKS"
exit $FAIL
