#!/usr/bin/env python3
"""ownership-check.py — verify a worktree's changed files against the released plan (used by gate.sh).

Usage: ownership-check.py <project> <worktree> <task-id[,task-id...]|@agents> <base-ref>

Every changed file in the product worktree (committed since base, staged, unstaged, untracked) must:
  - be listed in the tasks' owns_files (for "@agents": any agents-owned path — wave-level test writing)
  - be agents-owned in ownership.yml and not claimed in claims.md
  - not be under config.contracts_dir (contracts come from the plan, never from workers)
  - stay inside config.layout.folders (or be an allowed root file)
Plan files (ownership, claims, waves, config) are read from the released plan (runtime/plan).

Exit 0 = ok, 1 = violations, 2 = usage.
"""

import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agenthome import contracts_dir, find_home, in_layout, load_config, plan_dir  # noqa: E402
from ownership import claimed_by, load_claims, load_ownership, owner_of  # noqa: E402


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def changed_files(repo, base):
    files = set(filter(None, git(repo, "diff", "--name-only", f"{base}...HEAD").splitlines()))
    for line in git(repo, "status", "--porcelain", "--untracked-files=all").splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.add(path.strip('"'))
    return sorted(files)


def find_task(plan, task_id):
    for p in glob.glob(os.path.join(plan, "waves", "wave-*", "wave.json")):
        tasks = json.load(open(p)).get("tasks", {})
        if task_id in tasks:
            return tasks[task_id]
    return None


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    home = find_home(sys.argv[1])
    plan = plan_dir(home)
    worktree, task_ids, base = os.path.abspath(sys.argv[2]), sys.argv[3], sys.argv[4]
    cfg = load_config(plan)
    cdir = contracts_dir(cfg)

    allowed = None if task_ids == "@agents" else set()
    for task_id in ([] if allowed is None else task_ids.split(",")):
        task = find_task(plan, task_id)
        if task is None:
            print(f"ERROR task {task_id} not found in any released wave.json ({plan}/waves)")
            return 1
        allowed |= set(task.get("owns_files", []))

    areas, claims = load_ownership(plan), load_claims(plan)
    errors = []
    for f in changed_files(worktree, base):
        if allowed is not None and f not in allowed:
            errors.append(f"{f}: not in {task_ids} owns_files")
            continue
        if cdir and (f == cdir or f.startswith(cdir + "/")):
            errors.append(f"{f}: contracts ({cdir}/) come from the plan — Architect only")
            continue
        if not in_layout(cfg, f):
            errors.append(f"{f}: outside the product layout {cfg.get('layout', {}).get('folders')}")
        area = owner_of(areas, f)
        if area is None or area["owner"] != "agents":
            errors.append(f"{f}: owner is {area['owner'] if area else 'undefined'}, not agents")
        c = claimed_by(claims, f)
        if c:
            errors.append(f"{f}: claimed by {c['who']}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"ownership ({task_ids}): {'FAIL' if errors else 'PASS'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
