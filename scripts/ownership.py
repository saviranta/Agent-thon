"""ownership.py — parse ownership.yml and claims.md (in the agent home or the released plan), resolve owners
for product-repo paths.

Shared by check-wave.py (planning), chunks.py and ownership-check.py (gate). Standard library only.
The YAML subset supported is the one chunks.py writes:

areas:
  - path: "glob/**"
    owner: agents
    reviewers: ["@a", "@b"]
    change_rule: "text"
"""

import os
import re
from fnmatch import fnmatchcase


def _unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def _parse_list(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [_unquote(x) for x in v[1:-1].split(",") if x.strip()]
    return [_unquote(v)] if v else []


def load_ownership(d):
    """Areas from <d>/ownership.yml (d = agent home or plan dir): {path, owner, reviewers, change_rule}.
    Comma-separated paths expand to one area each. `areas: []` (nothing generated yet) → no areas."""
    path = os.path.join(d, "ownership.yml")
    areas, cur = [], None
    with open(path) as f:
        for raw in f:
            line = raw.split(" #")[0].rstrip() if not raw.lstrip().startswith("#") else ""
            if not line.strip():
                continue
            m = re.match(r"^\s*-\s*path:\s*(.+)$", line)
            if m:
                cur = {"path": _unquote(m.group(1)), "owner": None, "reviewers": [], "change_rule": ""}
                areas.append(cur)
                continue
            m = re.match(r"^\s+(owner|reviewers|change_rule):\s*(.*)$", line)
            if m and cur is not None:
                key, val = m.group(1), m.group(2)
                cur[key] = _parse_list(val) if key == "reviewers" else _unquote(val)
    expanded = []
    for a in areas:
        for p in [p.strip() for p in a["path"].split(",") if p.strip()]:
            expanded.append(dict(a, path=p))
    return expanded


def _glob_match(pattern, path):
    """Glob where ** spans directories and * stays within one segment."""
    regex = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            regex += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            regex += ".*"
            i += 2
        elif pattern[i] == "*":
            regex += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            regex += "[^/]"
            i += 1
        else:
            regex += re.escape(pattern[i])
            i += 1
    return re.fullmatch(regex, path) is not None


def _specificity(pattern):
    # More literal characters and fewer wildcards = more specific.
    return (len(pattern.replace("*", "")), -pattern.count("*"))


def owner_of(areas, path):
    """Return the most specific matching area for a repo-relative path, or None."""
    if path.startswith("./"):
        path = path[2:]
    matches = [a for a in areas if _glob_match(a["path"], path) or fnmatchcase(path, a["path"])]
    if not matches:
        return None
    return max(matches, key=lambda a: _specificity(a["path"]))


def load_claims(d):
    """Return a list of {who, path, until, note} from claims.md table rows."""
    path = os.path.join(d, "claims.md")
    claims = []
    if not os.path.exists(path):
        return claims
    with open(path) as f:
        for line in f:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or not line.strip().startswith("|"):
                continue
            if cells[0].lower() == "who" or set(cells[0]) <= set("-: "):
                continue
            claims.append({"who": cells[0], "path": cells[1].strip("`"),
                           "until": cells[2] if len(cells) > 2 else "",
                           "note": cells[3] if len(cells) > 3 else ""})
    return claims


def claimed_by(claims, path):
    for c in claims:
        p = c["path"]
        if _glob_match(p, path) or path == p or path.startswith(p.rstrip("/") + "/"):
            return c
    return None
