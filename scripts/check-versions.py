#!/usr/bin/env python3
"""check-versions.py — fail on non-exact dependency versions (no ^, ~, ranges, wildcards).

Usage: check-versions.py <project-root>
Checks every package.json (dependencies, devDependencies, peerDependencies, optionalDependencies)
and requirements*.txt outside node_modules/.venv/.agentthon. Exit 1 on violations.
"""

import json
import os
import re
import sys

SKIP_DIRS = {"node_modules", ".venv", "venv", ".git", ".agentthon", "dist", "build", "__pycache__"}
NPM_SECTIONS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
EXACT_NPM = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")
# Allowed non-semver specs that are still pinned: workspace/file links, git with commit hash, npm aliases with exact version.
ALLOWED_NPM = re.compile(r"^(workspace:\d|file:|link:|git\+.+#[0-9a-f]{7,}$|npm:[^@]+@\d+\.\d+\.\d+$)")
PY_REQ = re.compile(r"^\s*([A-Za-z0-9_.\-\[\]]+)\s*(.*)$")


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            yield os.path.join(d, f), f


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = os.path.abspath(sys.argv[1])
    errors = []
    for path, name in walk(root):
        rel = os.path.relpath(path, root)
        if name == "package.json":
            try:
                data = json.load(open(path))
            except ValueError as e:
                errors.append(f"{rel}: invalid JSON ({e})")
                continue
            for section in NPM_SECTIONS:
                for pkg, spec in (data.get(section) or {}).items():
                    if not (EXACT_NPM.match(spec) or ALLOWED_NPM.match(spec)):
                        errors.append(f"{rel}: {section}.{pkg} = \"{spec}\" is not an exact version")
        elif re.fullmatch(r"requirements.*\.txt", name):
            for i, line in enumerate(open(path), 1):
                line = line.split("#", 1)[0].strip()
                if not line or line.startswith(("-r", "-c", "--", "-e ")):
                    continue
                if "@" in line and "://" in line:
                    continue
                m = PY_REQ.match(line)
                spec = m.group(2).split(";")[0].strip() if m else ""
                if not re.fullmatch(r"==\s*[\w.+!-]+", spec):
                    errors.append(f"{rel}:{i}: \"{line}\" is not pinned with ==")
    for e in errors:
        print(f"ERROR {e}")
    print(f"versions: {'FAIL' if errors else 'PASS'} ({len(errors)} problem(s))")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
