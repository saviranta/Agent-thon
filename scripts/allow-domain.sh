#!/bin/bash
# allow-domain.sh — add network domains to a project's sandbox allowlist (config.network.allowed_domains)
#
# Usage: allow-domain.sh <project> <domain> [domain...]
# The Architect proposes domains; run this only after the user has approved them.
# The list is shared via the agent home (commit config.json); run-agent.sh applies it at the next start.

set -euo pipefail
source "$(dirname "$0")/lib.sh"

H="$(resolve_project "${1:-}")"
shift || true
[[ $# -ge 1 ]] || die "Usage: allow-domain.sh <project> <domain> [domain...]"

for d in "$@"; do
  [[ "$d" =~ ^(\*\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]] || die "Not a domain: $d"
done

CFG_FILE="$H/config.json" python3 - "$@" <<'PY'
import json, os, sys
p = os.environ["CFG_FILE"]
c = json.load(open(p))
lst = c.setdefault("network", {}).setdefault("allowed_domains", [])
for d in sys.argv[1:]:
    if d not in lst:
        lst.append(d)
        print(f"added {d}")
    else:
        print(f"already allowed {d}")
json.dump(c, open(p, "w"), indent=2)
open(p, "a").write("\n")
PY
echo "Commit config.json in the agent home. Restart running agents in this project to apply."
