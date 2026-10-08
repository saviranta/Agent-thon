#!/usr/bin/env python3
"""check-wave.py — deterministic checks for a planned wave (no LLM, no tokens).

Usage: check-wave.py <project-root> <wave-number>
Exit 0 = no errors (warnings allowed), 1 = errors.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ownership import claimed_by, load_claims, load_ownership, owner_of  # noqa: E402

BUILDERS = {"builder-infra", "builder-api", "builder-extraction", "builder-ai-integration",
            "builder-ui", "builder-composer"}
TAGS = {"api", "extraction", "ai", "domain", "ui", "infra", "security"}
SIZES = {"S", "M"}
MAX_FILES = 4
MAX_SPEC_LINES = 60      # specs point to contracts/context packs instead of copying them
MAX_SPEC_CHARS = 3500
MAX_TASK_ENTRY_CHARS = 900  # wave.json is an index, not prose


def load_wave(project, n):
    path = os.path.join(project, ".agentthon", "waves", f"wave-{n}", "wave.json")
    with open(path) as f:
        return json.load(f), path


def earlier_task_ids(project, n):
    ids = set()
    waves_dir = os.path.join(project, ".agentthon", "waves")
    for name in os.listdir(waves_dir):
        m = re.fullmatch(r"wave-(\d+)", name)
        if m and int(m.group(1)) < n:
            p = os.path.join(waves_dir, name, "wave.json")
            if os.path.exists(p):
                ids.update(json.load(open(p)).get("tasks", {}).keys())
    return ids


def ancestors(tasks, tid, seen=None):
    seen = set() if seen is None else seen
    for d in tasks.get(tid, {}).get("depends_on", []):
        if d not in seen:
            seen.add(d)
            ancestors(tasks, d, seen)
    return seen


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    project, n = os.path.abspath(sys.argv[1]), int(sys.argv[2])
    errors, warnings = [], []
    err, warn = errors.append, warnings.append

    try:
        wave, wave_path = load_wave(project, n)
    except FileNotFoundError:
        print(f"ERROR wave file missing: .agentthon/waves/wave-{n}/wave.json")
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR wave.json is not valid JSON: {e}")
        return 1

    if "FILL_IN" in open(wave_path).read():
        err("wave.json still contains FILL_IN placeholders")
    if wave.get("wave") != n:
        err(f"wave.json 'wave' is {wave.get('wave')}, expected {n}")

    tasks = wave.get("tasks", {})
    if not tasks:
        err("wave has no tasks")
    prior = earlier_task_ids(project, n)
    for tid in tasks:
        if tid in prior:
            err(f"{tid}: id already used in an earlier wave")

    areas = load_ownership(project)
    claims = load_claims(project)
    agentthon = os.path.join(project, ".agentthon")

    for tid, t in tasks.items():
        p = f"{tid}:"
        if t.get("type", "implementation") != "implementation":
            err(f"{p} type must be 'implementation' (review/test gates are run by the Foreman, not planned as tasks)")
        if t.get("assigned_to") not in BUILDERS:
            err(f"{p} assigned_to '{t.get('assigned_to')}' is not one of {sorted(BUILDERS)}")
        if t.get("size") not in SIZES:
            err(f"{p} size must be S or M (split larger tasks)")
        bad_tags = set(t.get("tags", [])) - TAGS
        if bad_tags:
            err(f"{p} unknown tags {sorted(bad_tags)}")

        files = t.get("owns_files", [])
        if not files:
            err(f"{p} owns_files is empty")
        if len(files) > MAX_FILES:
            err(f"{p} owns {len(files)} files (max {MAX_FILES}) — split the task")
        for f in files:
            if f.startswith("contracts/"):
                err(f"{p} {f}: contracts are written by the Architect, not by tasks")
                continue
            area = owner_of(areas, f)
            if area is None:
                err(f"{p} {f}: no ownership area matches — add it to ownership.yml")
            elif area["owner"] != "agents":
                err(f"{p} {f}: owned by '{area['owner']}' (area {area['path']}), agents may not write here")
            c = claimed_by(claims, f)
            if c:
                err(f"{p} {f}: claimed by {c['who']} until {c['until'] or '?'}")

        for d in t.get("depends_on", []):
            if d not in tasks and d not in prior:
                err(f"{p} depends_on unknown task {d}")
        if tid in ancestors(tasks, tid):
            err(f"{p} dependency cycle")

        if any(tid in o.get("depends_on", []) for o in tasks.values()) and not t.get("provides"):
            warn(f"{p} other tasks depend on it but it has no 'provides' (the interface they use)")
        if len(json.dumps(t)) > MAX_TASK_ENTRY_CHARS:
            warn(f"{p} wave.json entry is {len(json.dumps(t))} chars (cap {MAX_TASK_ENTRY_CHARS}) — keep detail in the spec")

        spec_rel = t.get("spec_file", "")
        spec = os.path.join(agentthon, spec_rel)
        if not spec_rel or not os.path.exists(spec):
            err(f"{p} spec file missing: .agentthon/{spec_rel}")
        else:
            text = open(spec).read()
            if "FILL_IN" in text or re.search(r"\[exact/path", text):
                err(f"{p} spec still contains template placeholders")
            ut = re.search(r"^## Unit tests.*?$(.*?)(^## |\Z)", text, re.S | re.M)
            if not ut or not re.search(r"^\s*-\s+\S", ut.group(1), re.M):
                err(f"{p} spec has no unit tests listed")
            if not re.search(r"^## Acceptance criteria", text, re.M):
                err(f"{p} spec has no acceptance criteria")
            nlines, nchars = text.count("\n") + 1, len(text)
            if nlines > MAX_SPEC_LINES or nchars > MAX_SPEC_CHARS:
                warn(f"{p} spec is {nlines} lines / {nchars} chars (cap {MAX_SPEC_LINES} / {MAX_SPEC_CHARS}) "
                     "— point to contracts/context packs instead of copying them")
            for f in files:
                if f not in text:
                    warn(f"{p} owned file {f} is not mentioned in the spec")

        is_ui = t.get("assigned_to") == "builder-ui" or "ui" in t.get("tags", [])
        if is_ui:
            ref = wave.get("ui_freeze_ref")
            if not ref or not os.path.exists(os.path.join(project, ref)):
                err(f"{p} UI task but wave ui_freeze_ref is missing or does not exist ({ref})")
        if "ai" in t.get("tags", []) and "domain" not in t.get("tags", []):
            warn(f"{p} tagged 'ai' without 'domain' — add 'domain' if its output is shown to users as domain information")

    # Parallel file overlap: shared files only along a dependency chain.
    ids = list(tasks)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            shared = set(tasks[a].get("owns_files", [])) & set(tasks[b].get("owns_files", []))
            if shared and a not in ancestors(tasks, b) and b not in ancestors(tasks, a):
                err(f"{a} and {b} can run in parallel but both own {sorted(shared)}")

    wt = wave.get("wave_tests", {})
    if not wt.get("integration"):
        warn("wave_tests.integration is empty")
    if not wt.get("e2e"):
        warn("wave_tests.e2e is empty")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\nwave-{n}: {len(tasks)} tasks, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
