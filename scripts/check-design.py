#!/usr/bin/env python3
"""check-design.py — flag raw colour values in agent-built UI code (used by gate.sh as the `design` check).

Usage: check-design.py <project> <work-dir> [<base-ref>]

Scans files that match config.design.ui_paths, are agents-owned and are not in config.design.theme_paths
(the theme/tokens files are the only place raw values belong). With <base-ref>, only files changed since it.
Test files are skipped. Flags:
  - hex colours (#fff, #1a2b3c, bg-[#123456])
  - rgb()/hsl()/oklch() with literal numbers (rgb(var(--x)) is fine)
  - Tailwind palette classes (bg-blue-500, text-zinc-700) unless config.design.allow_palette_classes is true
A line containing `design-ok` is ignored (use sparingly, with a reason).
No config.design.ui_paths → skipped (exit 0). Exit 0 = ok, 1 = findings, 2 = usage.
"""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agenthome import find_home, load_config, plan_dir  # noqa: E402
from ownership import _glob_match, load_ownership, owner_of  # noqa: E402

EXTS = {".tsx", ".jsx", ".ts", ".js", ".mjs", ".vue", ".svelte", ".astro", ".css", ".scss", ".sass",
        ".less", ".html", ".mdx", ".py"}
TEST = re.compile(r"(^|/)(__tests__|tests?|e2e)/|\.(test|spec|stories)\.[a-z]+$")
HEX = re.compile(r"(?<![\w&/])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")
FUNC = re.compile(r"\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\(\s*[\d.][^)]*\)")
LINK = re.compile(r"""(?:href|to|xlink:href)=\{?["'`]$""")  # "#section" anchors, not colours
PALETTE = re.compile(
    r"\b(?:bg|text|border|ring|fill|stroke|from|via|to|outline|decoration|divide|accent|caret|placeholder|shadow)"
    r"-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo"
    r"|violet|purple|fuchsia|pink|rose)-\d{2,3}\b")


def git(wd, *args):
    return subprocess.run(["git", "-C", wd, *args], capture_output=True, text=True, check=True).stdout


def candidate_files(wd, base):
    if base:
        files = set(filter(None, git(wd, "diff", "--name-only", f"{base}...HEAD").splitlines()))
        for line in git(wd, "status", "--porcelain", "--untracked-files=all").splitlines():
            path = line[3:]
            files.add((path.split(" -> ", 1)[1] if " -> " in path else path).strip('"'))
    else:
        files = set(git(wd, "ls-files", "--cached", "--others", "--exclude-standard").splitlines())
    return sorted(f for f in files if os.path.isfile(os.path.join(wd, f)))


def matches(globs, path):
    return any(_glob_match(g, path) or path == g for g in globs)


def main():
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        return 2
    plan = plan_dir(find_home(sys.argv[1]))
    wd = os.path.abspath(sys.argv[2])
    base = sys.argv[3] if len(sys.argv) == 4 else None
    design = load_config(plan).get("design", {}) or {}
    ui_paths, theme_paths = design.get("ui_paths") or [], design.get("theme_paths") or []
    if not ui_paths:
        print("design: config.design.ui_paths not set — skipped")
        return 0
    patterns = [("colour literal", HEX), ("colour function", FUNC)]
    if not design.get("allow_palette_classes"):
        patterns.append(("palette class", PALETTE))
    areas = load_ownership(plan)

    findings, scanned = [], 0
    for f in candidate_files(wd, base):
        if os.path.splitext(f)[1] not in EXTS or TEST.search(f):
            continue
        if not matches(ui_paths, f) or matches(theme_paths, f):
            continue
        area = owner_of(areas, f)
        if area is None or area["owner"] != "agents":
            continue
        scanned += 1
        with open(os.path.join(wd, f), errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if "design-ok" in line:
                    continue
                for kind, rx in patterns:
                    for m in rx.finditer(line):
                        if kind == "colour literal" and LINK.search(line[:m.start()]):
                            continue
                        findings.append(f"{f}:{i}: {kind} '{m.group(0)}'")

    for x in findings:
        print(x)
    if findings:
        print(f"\ndesign: {len(findings)} raw values in {scanned} UI files — use the design tokens "
              f"(theme files: {', '.join(theme_paths) or 'config.design.theme_paths not set'}; "
              "see the plan's artifacts/ui/design-system.md)")
        return 1
    print(f"design: ok ({scanned} UI files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
