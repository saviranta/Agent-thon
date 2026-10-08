#!/bin/bash
# allow-domain.sh — add network domains to a project's sandbox allowlist (.claude/settings.json)
#
# Usage: allow-domain.sh <project> <domain> [domain...]
# The Architect proposes domains; run this only after the user has approved them.

set -euo pipefail
source "$(dirname "$0")/lib.sh"

PROJECT_ROOT="$(resolve_project "${1:-}")"
shift || true
[[ $# -ge 1 ]] || die "Usage: allow-domain.sh <project> <domain> [domain...]"

SETTINGS="$PROJECT_ROOT/.claude/settings.json"
for d in "$@"; do
  [[ "$d" =~ ^(\*\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]] || die "Not a domain: $d"
done

SETTINGS_FILE="$SETTINGS" python3 - "$@" <<'EOF'
import json, os, sys
p = os.environ["SETTINGS_FILE"]
s = json.load(open(p))
lst = s.setdefault("sandbox", {}).setdefault("network", {}).setdefault("allowedDomains", [])
for d in sys.argv[1:]:
    if d not in lst:
        lst.append(d)
        print(f"added {d}")
    else:
        print(f"already allowed {d}")
json.dump(s, open(p, "w"), indent=2)
open(p, "a").write("\n")
EOF
echo "Restart running agents in this project to apply."
