#!/usr/bin/env python3
"""ownership-check.py — verify changed files against ownership.yml, claims and (for tasks) owns_files.

Task mode (gate, inside a task worktree):
  ownership-check.py task <worktree> <task-id[,task-id...]> <base-ref>
    Every changed file (for several ids: the union of their owns_files; the id "@agents" allows any
    agents-owned path, used for wave-level test writing) (committed since base, staged, unstaged, untracked) must be listed in the
    task's owns_files, be agents-owned, not be under contracts/, and not be claimed.

PR mode (CI, any PR):
  ownership-check.py pr <repo-dir> <base-ref> <head-branch>
    agentthon/* branches: only agents-owned paths (+ .agentthon/evals/reports/**).
    plan/* branches: only architect-owned paths (.agentthon/**, contracts/**, generated and team files).
    other (human) branches: never fail on ownership — list the owners whose areas are touched
    (GitHub CODEOWNERS enforces approvals) and warn about claimed or agent-owned paths.

Exit 0 = ok, 1 = violations.
"""

import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ownership import _glob_match, claimed_by, load_claims, load_ownership, owner_of  # noqa: E402


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def changed_files(repo, base, include_worktree):
    files = set(filter(None, git(repo, "diff", "--name-only", f"{base}...HEAD").splitlines()))
    if include_worktree:
        for line in git(repo, "status", "--porcelain", "--untracked-files=all").splitlines():
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            files.add(path.strip('"'))
    return sorted(f for f in files if not f.startswith(".agentthon/runtime/"))


def find_task(repo, task_id):
    for p in glob.glob(os.path.join(repo, ".agentthon", "waves", "wave-*", "wave.json")):
        tasks = json.load(open(p)).get("tasks", {})
        if task_id in tasks:
            return tasks[task_id]
    return None


def task_mode(repo, task_ids, base):
    allowed = None if task_ids == "@agents" else set()
    for task_id in ([] if allowed is None else task_ids.split(",")):
        task = find_task(repo, task_id)
        if task is None:
            print(f"ERROR task {task_id} not found in any wave.json")
            return 1
        allowed |= set(task.get("owns_files", []))
    task_id = task_ids
    areas, claims = load_ownership(repo), load_claims(repo)
    errors = []
    for f in changed_files(repo, base, include_worktree=True):
        if allowed is not None and f not in allowed:
            errors.append(f"{f}: not in {task_id} owns_files")
            continue
        if f.startswith("contracts/"):
            errors.append(f"{f}: contracts are Architect-only")
        area = owner_of(areas, f)
        if area is None or area["owner"] != "agents":
            errors.append(f"{f}: owner is {area['owner'] if area else 'undefined'}, not agents")
        c = claimed_by(claims, f)
        if c:
            errors.append(f"{f}: claimed by {c['who']}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"ownership ({task_id}): {'FAIL' if errors else 'PASS'}")
    return 1 if errors else 0


def pr_mode(repo, base, head):
    areas, claims = load_ownership(repo), load_claims(repo)
    files = changed_files(repo, base, include_worktree=False)
    errors, warnings, owners = [], [], {}
    for f in files:
        area = owner_of(areas, f)
        owner = area["owner"] if area else "undefined"
        owners.setdefault(owner, []).append(f)
        if head.startswith("agentthon/"):
            if f.startswith(".agentthon/evals/reports/"):
                continue
            if owner != "agents":
                errors.append(f"{f}: agent branch may only change agents-owned paths (owner: {owner})")
        elif head.startswith("plan/"):
            if owner != "architect":
                errors.append(f"{f}: plan branch may only change architect-owned paths (owner: {owner})")
        else:
            if owner == "agents":
                warnings.append(f"{f}: agent-owned area — coordinate with the Architect")
            if owner in ("architect", "shared") and area and area.get("change_rule"):
                warnings.append(f"{f}: {owner} area — rule: {area['change_rule']}")
            c = claimed_by(claims, f)
            if c:
                warnings.append(f"{f}: claimed by {c['who']}")
    for owner, fs in sorted(owners.items()):
        print(f"OWNER {owner}: {len(fs)} file(s)")
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"ownership (PR {head}): {'FAIL' if errors else 'PASS'}")
    return 1 if errors else 0


def main():
    if len(sys.argv) == 5 and sys.argv[1] == "task":
        return task_mode(os.path.abspath(sys.argv[2]), sys.argv[3], sys.argv[4])
    if len(sys.argv) == 5 and sys.argv[1] == "pr":
        return pr_mode(os.path.abspath(sys.argv[2]), sys.argv[3], sys.argv[4])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
