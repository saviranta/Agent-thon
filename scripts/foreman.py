#!/usr/bin/env python3
"""foreman.py — deterministic mechanics for the Foreman agent (no LLM).

Usage: foreman.py <project> <command> [args]     (<project> = agent home or the product repo next to it)

Plan vs product: released waves are read from runtime/plan — a detached worktree of the agent home at its
main (origin/main when shared). All branches, worktrees and PRs are in the product repo.

Waves
  ingest                      refresh runtime/plan from the agent home's main, add newly released waves/tasks to state
  wait [seconds]              poll until a pending wave exists (default 540s); exit 0 found / 3 timeout
  wave-start <N>              create the wave branch (stacked on an open previous wave if needed) in the foreman
                              worktree and sync the plan's contracts into it (one commit)
  wave-sync <N>               merge main (and open base wave) into wave N, re-sync contracts; exit 2 on conflict
  wave-set <N> <key> <json>   set a wave field (status, etc.)
  open-pr <N>                 push wave branch and open the PR with a generated body (or write body if no remote)
  pr-body <N>                 print the PR body

Tasks
  ready <N>                   JSON list of tasks to dispatch now (deps merged, no overlap, not claimed, ≤ parallel_workers)
  task-start <id>             create/reuse task worktree + branch from the wave branch; prints worktree path
  task-merge <id>             merge task branch into wave branch, remove worktree; exit 2 on conflict
  task-park <id> <reason>     park task, add a question for the Architect
  task-set <id> <key> <json>  set a task field
  attempt <id> <severity>     count a fix attempt (critical|standard|polish); prints OK n/max or EXHAUSTED
  reconcile                   after resume: report in-progress tasks and their worktree state

Wave-level work (fixes after wave review, wave tests, eval reports)
  fix-start <N> <label> [task-ids]   worktree runtime/worktrees/<label> on branch <wave branch>-<label> from the wave branch;
                                     task-ids (comma-separated) = whose owns_files the fix may touch (ownership check)
  fix-merge <label>                  merge it into the wave branch and remove the worktree; exit 2 on conflict

Results and status
  result <id> <step>          print compact verdict from runtime/results/<id>/<step>.json
  log <agent> <task|-> [note] append to runtime/usage-log.jsonl
  question <text>             question for the Architect: runtime/questions.md + issue labelled foreman-question in
                              the agent home repo (when shared)
  status                      regenerate runtime/status.md
  profile                     print active profile settings as JSON
"""

import datetime
import glob
import json
import os
import re
import subprocess
import sys

TOOLKIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(TOOLKIT, "scripts"))
from agenthome import find_home, repo_of  # noqa: E402
from ownership import claimed_by, load_claims  # noqa: E402

SEVERITIES = ("critical", "standard", "polish")


def now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


class Project:
    def __init__(self, path):
        self.home = find_home(path)
        self.root = repo_of(self.home)          # product repo: all git work happens here
        self.rt = os.path.join(self.home, "runtime")
        self.plan = os.path.join(self.rt, "plan")
        self.wt_dir = os.path.join(self.rt, "worktrees")
        self.foreman_wt = os.path.join(self.wt_dir, "foreman")
        self.state_path = os.path.join(self.rt, "state.json")
        os.makedirs(self.wt_dir, exist_ok=True)
        os.makedirs(os.path.join(self.rt, "results"), exist_ok=True)
        if not os.path.exists(self.state_path):
            json.dump({"version": 1, "waves": {}, "tasks": {}, "paused": None}, open(self.state_path, "w"))
        self.state = json.load(open(self.state_path))
        self.state.setdefault("waves", {})
        self.state.setdefault("tasks", {})

    # ── state ──
    def save(self, step=None):
        self.state["updated_at"] = now()
        if step:
            self.state["last_step"] = step
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.state, f, indent=2)
        os.replace(tmp, self.state_path)

    # ── config ──
    def config(self):
        """The released plan's config (runtime/plan), else the agent home's."""
        path = os.path.join(self.plan, "config.json")
        if not os.path.exists(path):
            path = os.path.join(self.home, "config.json")
        return json.load(open(path))

    def plan_dir(self):
        return self.plan if os.path.exists(os.path.join(self.plan, "config.json")) else self.home

    def profile(self):
        cfg = json.load(open(os.path.join(self.home, "config.json")))
        local = os.path.join(self.rt, "local.json")
        name = cfg.get("profile")
        if os.path.exists(local):
            name = json.load(open(local)).get("profile") or name
        prof = dict(cfg["profiles"][name])
        prof["name"] = name
        return prof

    # ── git ──
    def git(self, *args, cwd=None, check=True):
        r = subprocess.run(["git", "-C", cwd or self.root, *args], capture_output=True, text=True)
        if check and r.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
        return r

    def has_remote(self):
        return self.git("remote", "get-url", "origin", check=False).returncode == 0

    def main_ref(self):
        main = self.config().get("git", {}).get("main_branch", "main")
        return f"origin/{main}" if self.has_remote() else main

    def fetch(self):
        if self.has_remote():
            self.git("fetch", "--quiet", "origin")

    def wave_branch(self, n):
        return self.config()["git"].get("wave_branch_prefix", "agentthon/wave-") + str(n)

    def task_branch(self, tid):
        prefix = self.config()["git"].get("task_branch_prefix", "agentthon/task-")
        return prefix + tid.replace("task-", "", 1) if tid.startswith("task-") else prefix + tid

    def branch_exists(self, branch):
        return self.git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode == 0

    def question(self, text):
        path = os.path.join(self.rt, "questions.md")
        existing = open(path).read() if os.path.exists(path) else ""
        n = len(re.findall(r"^## Q-\d+", existing, re.M)) + 1
        qid = f"Q-{n:03d}"
        url = ""
        gh_repo = self.config().get("git", {}).get("agents_github_repo")
        if gh_repo:
            r = subprocess.run(["gh", "issue", "create", "-R", gh_repo, "--label", "foreman-question",
                                "--title", f"{qid}: {text.splitlines()[0][:80]}", "--body", text],
                               capture_output=True, text=True)
            if r.returncode == 0:
                url = r.stdout.strip().splitlines()[-1]
        with open(path, "a") as f:
            f.write(f"\n## {qid} ({now()}) — OPEN{' ' + url if url else ''}\n{text}\n")
        return qid

    def refresh_plan(self):
        """Point runtime/plan at the agent home's released main (origin/main when shared)."""
        main = "main"
        try:
            main = json.load(open(os.path.join(self.home, "config.json"))).get("git", {}).get("main_branch", "main")
        except ValueError:
            pass
        ref = main
        if self.git("remote", "get-url", "origin", cwd=self.home, check=False).returncode == 0:
            self.git("fetch", "--quiet", "origin", cwd=self.home, check=False)
            if self.git("rev-parse", "--verify", "--quiet", f"origin/{main}", cwd=self.home, check=False).returncode == 0:
                ref = f"origin/{main}"
        if not os.path.isdir(self.plan):
            self.git("worktree", "prune", cwd=self.home, check=False)
            self.git("worktree", "add", "--quiet", "--detach", self.plan, ref, cwd=self.home)
        else:
            self.git("checkout", "--quiet", "--detach", ref, cwd=self.plan)
        return ref, self.git("rev-parse", "--short", "HEAD", cwd=self.plan).stdout.strip()

    def sync_contracts(self, n):
        r = subprocess.run([sys.executable, os.path.join(TOOLKIT, "scripts", "contracts.py"), self.home, "sync",
                            self.foreman_wt, f"[wave-{n}] contracts: sync from the released plan"],
                           capture_output=True, text=True)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise RuntimeError(f"contracts sync failed: {r.stderr.strip() or r.stdout.strip()}")


# ── commands ──

def cmd_ingest(p, *_):
    p.fetch()
    plan_ref, plan_sha = p.refresh_plan()
    waves_dir = os.path.join(p.plan, "waves")
    entries = sorted(os.listdir(waves_dir)) if os.path.isdir(waves_dir) else []
    added = []
    for entry in entries:
        m = re.fullmatch(r"wave-(\d+)", entry)
        if not m or m.group(1) in p.state["waves"]:
            continue
        path = os.path.join(waves_dir, entry, "wave.json")
        if not os.path.exists(path):
            continue
        wave = json.load(open(path))
        n = m.group(1)
        p.state["waves"][n] = {"status": "pending", "title": wave.get("title"), "goal": wave.get("goal"),
                               "eval_required": bool(wave.get("eval_required")), "milestone": bool(wave.get("milestone")),
                               "ingested_at": now()}
        for tid, t in wave.get("tasks", {}).items():
            p.state["tasks"][tid] = {"wave": int(n), "title": t.get("title"), "assigned_to": t.get("assigned_to"),
                                     "tags": t.get("tags", []), "depends_on": t.get("depends_on", []),
                                     "owns_files": t.get("owns_files", []), "spec_file": t.get("spec_file"),
                                     "status": "pending", "attempts": {s: 0 for s in SEVERITIES}}
        added.append(n)
    refresh_prs(p)
    p.state["plan"] = {"ref": plan_ref, "commit": plan_sha, "at": now()}
    p.save("ingest")
    pending = sorted((int(n) for n, w in p.state["waves"].items() if w["status"] == "pending"))
    print(json.dumps({"new_waves": added, "pending_waves": pending, "plan": f"{plan_ref} {plan_sha}"}))


def refresh_prs(p):
    """Mark waves whose PR was merged (or closed) on GitHub."""
    for n, w in p.state["waves"].items():
        if w.get("status") != "pr_open" or not w.get("pr_url"):
            continue
        r = subprocess.run(["gh", "pr", "view", w["pr_url"], "--json", "state", "-q", ".state"],
                           cwd=p.root, capture_output=True, text=True)
        state = r.stdout.strip()
        if state == "MERGED":
            w.update(status="merged", merged_at=now())
        elif state == "CLOSED":
            w.update(status="closed")


def cmd_wait(p, seconds="540"):
    import time
    deadline = time.time() + int(seconds)
    while True:
        cmd_ingest_quiet(p)
        pending = [n for n, w in p.state["waves"].items() if w["status"] == "pending"]
        if pending:
            print(json.dumps({"pending_waves": sorted(map(int, pending))}))
            return 0
        if time.time() >= deadline:
            print(json.dumps({"pending_waves": [], "timeout": True}))
            return 3
        time.sleep(60)


def cmd_ingest_quiet(p):
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        cmd_ingest(p)


def open_base_wave(p, n):
    """Return the previous wave's branch if its PR is still open (stacking), else None."""
    prev = p.state["waves"].get(str(int(n) - 1))
    if prev and prev.get("status") in ("building", "reviewing", "wave_tests", "pr_open") and p.branch_exists(p.wave_branch(int(n) - 1)):
        return p.wave_branch(int(n) - 1)
    return None


def cmd_wave_start(p, n):
    p.fetch()
    branch = p.wave_branch(n)
    base = open_base_wave(p, n) or p.main_ref()
    if not p.branch_exists(branch):
        p.git("branch", branch, base)
    if not os.path.isdir(p.foreman_wt):
        p.git("worktree", "add", "--quiet", p.foreman_wt, branch)
    else:
        if p.git("status", "--porcelain", cwd=p.foreman_wt).stdout.strip():
            sys.exit("Foreman worktree has uncommitted changes — commit or clean them first")
        p.git("checkout", "--quiet", branch, cwd=p.foreman_wt)
    sync = p.sync_contracts(n)
    w = p.state["waves"][str(n)]
    w.update(status="building", branch=branch, base=base, started_at=w.get("started_at") or now(),
             profile=p.profile()["name"], contracts_synced=bool(sync.get("changed")) or w.get("contracts_synced", False))
    p.save(f"wave-start {n}")
    print(json.dumps({"wave": int(n), "branch": branch, "base": base, "worktree": p.foreman_wt, "contracts": sync}))


def cmd_wave_sync(p, n):
    p.fetch()
    sources = [p.main_ref()]
    base = open_base_wave(p, n)
    if base:
        sources.append(base)
    merged = []
    for src in sources:
        r = p.git("merge", "--no-edit", "--quiet", src, cwd=p.foreman_wt, check=False)
        if r.returncode != 0:
            conflicts = p.git("diff", "--name-only", "--diff-filter=U", cwd=p.foreman_wt, check=False).stdout.split()
            p.git("merge", "--abort", cwd=p.foreman_wt, check=False)
            print(json.dumps({"conflict_with": src, "files": conflicts}))
            return 2
        merged.append(src)
    if p.sync_contracts(n).get("changed"):
        p.state["waves"][str(n)]["contracts_synced"] = True
    p.state["waves"][str(n)]["synced_at"] = now()
    p.save(f"wave-sync {n}")
    print(json.dumps({"synced": merged}))
    return 0


def cmd_wave_set(p, n, key, value):
    p.state["waves"][str(n)][key] = json.loads(value)
    p.save(f"wave-set {n} {key}")


def cmd_ready(p, n):
    prof = p.profile()
    limit = int(prof.get("parallel_workers", 1))
    tasks = p.state["tasks"]
    claims = load_claims(p.plan_dir())
    busy = [t for t in tasks.values() if t["status"] == "in_progress"]
    busy_files = {f for t in busy for f in t["owns_files"]}
    slots = max(0, limit - len(busy))
    chosen, skipped = [], []
    for tid, t in sorted(tasks.items()):
        if t["wave"] != int(n) or t["status"] != "pending":
            continue
        deps_ok = all(tasks.get(d, {}).get("status") == "merged" for d in t["depends_on"])
        if not deps_ok:
            continue
        claim = next((claimed_by(claims, f) for f in t["owns_files"] if claimed_by(claims, f)), None)
        if claim:
            skipped.append({"id": tid, "reason": f"claimed by {claim['who']}"})
            continue
        if busy_files & set(t["owns_files"]):
            continue
        if len(chosen) >= slots:
            break
        chosen.append({"id": tid, "assigned_to": t["assigned_to"], "tags": t["tags"],
                       "spec": os.path.join(p.plan_dir(), t["spec_file"]) if t.get("spec_file") else None})
        busy_files |= set(t["owns_files"])
    remaining = [tid for tid, t in tasks.items() if t["wave"] == int(n) and t["status"] not in ("merged", "parked")]
    print(json.dumps({"dispatch": chosen, "skipped": skipped, "in_progress": [t for t, v in tasks.items() if v["status"] == "in_progress"],
                      "remaining_in_wave": len(remaining), "parallel_workers": limit}))


def cmd_task_start(p, tid):
    t = p.state["tasks"][tid]
    wt = os.path.join(p.wt_dir, tid)
    branch = p.task_branch(tid)
    if not os.path.isdir(wt):
        if p.branch_exists(branch):
            p.git("worktree", "add", "--quiet", wt, branch)
        else:
            p.git("worktree", "add", "--quiet", "-b", branch, wt, p.wave_branch(t["wave"]))
    base = p.git("merge-base", branch, p.wave_branch(t["wave"])).stdout.strip()
    t.update(status="in_progress", worktree=wt, branch=branch, base=base, started_at=t.get("started_at") or now())
    p.save(f"task-start {tid}")
    print(json.dumps({"task": tid, "worktree": wt, "branch": branch, "base": base}))


def cmd_task_merge(p, tid):
    t = p.state["tasks"][tid]
    wt, branch = t["worktree"], t["branch"]
    if p.git("status", "--porcelain", cwd=wt).stdout.strip():
        p.git("add", "-A", cwd=wt)
        p.git("commit", "--quiet", "-m", f"[{tid}] work: {t['title']}", cwd=wt)
    ahead = p.git("rev-list", "--count", f"{p.wave_branch(t['wave'])}..{branch}").stdout.strip()
    if ahead == "0":
        sys.exit(f"{tid}: task branch has no commits to merge")
    r = p.git("merge", "--no-ff", "--quiet", "-m", f"[{tid}] {t['title']}", branch, cwd=p.foreman_wt, check=False)
    if r.returncode != 0:
        conflicts = p.git("diff", "--name-only", "--diff-filter=U", cwd=p.foreman_wt, check=False).stdout.split()
        p.git("merge", "--abort", cwd=p.foreman_wt, check=False)
        print(json.dumps({"conflict": True, "files": conflicts}))
        return 2
    p.git("worktree", "remove", "--force", wt)
    p.git("branch", "-D", branch, check=False)
    t.update(status="merged", merged_at=now(), worktree=None)
    p.save(f"task-merge {tid}")
    print(json.dumps({"merged": tid}))
    return 0


def cmd_fix_start(p, n, label, task_ids=""):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", label):
        sys.exit("label may contain letters, digits, '.', '_' and '-' only")
    wt = os.path.join(p.wt_dir, label)
    branch = f"{p.wave_branch(n)}-{label}"
    if not os.path.isdir(wt):
        if p.branch_exists(branch):
            p.git("worktree", "add", "--quiet", wt, branch)
        else:
            p.git("worktree", "add", "--quiet", "-b", branch, wt, p.wave_branch(n))
    base = p.git("merge-base", branch, p.wave_branch(n)).stdout.strip()
    fixes = p.state.setdefault("fixes", {})
    fixes[label] = {"wave": int(n), "worktree": wt, "branch": branch, "base": base,
                    "tasks": [t for t in task_ids.split(",") if t], "started_at": now()}
    p.save(f"fix-start {n} {label}")
    print(json.dumps({"label": label, "worktree": wt, "branch": branch, "base": base, "ownership_tasks": task_ids or None}))


def cmd_fix_merge(p, label):
    f = p.state.get("fixes", {}).get(label)
    if not f:
        sys.exit(f"unknown fix worktree: {label}")
    wt, branch = f["worktree"], f["branch"]
    if p.git("status", "--porcelain", cwd=wt).stdout.strip():
        p.git("add", "-A", cwd=wt)
        p.git("commit", "--quiet", "-m", f"[wave-{f['wave']}] {label}", cwd=wt)
    if p.git("rev-list", "--count", f"{p.wave_branch(f['wave'])}..{branch}").stdout.strip() == "0":
        p.git("worktree", "remove", "--force", wt)
        p.git("branch", "-D", branch, check=False)
        del p.state["fixes"][label]
        p.save(f"fix-merge {label} (nothing to merge)")
        print(json.dumps({"merged": label, "note": "no changes"}))
        return 0
    r = p.git("merge", "--no-ff", "--quiet", "-m", f"[wave-{f['wave']}] {label}", branch, cwd=p.foreman_wt, check=False)
    if r.returncode != 0:
        conflicts = p.git("diff", "--name-only", "--diff-filter=U", cwd=p.foreman_wt, check=False).stdout.split()
        p.git("merge", "--abort", cwd=p.foreman_wt, check=False)
        print(json.dumps({"conflict": True, "files": conflicts}))
        return 2
    p.git("worktree", "remove", "--force", wt)
    p.git("branch", "-D", branch, check=False)
    del p.state["fixes"][label]
    p.save(f"fix-merge {label}")
    print(json.dumps({"merged": label}))
    return 0


def cmd_task_park(p, tid, reason):
    t = p.state["tasks"][tid]
    q = p.question(f"Task {tid} ({t['title']}) parked.\nReason: {reason}\n"
                   f"Branch kept: {t.get('branch')} (product repo). Spec: {t.get('spec_file')} (agent home)\n"
                   f"Architect: re-spec, split, cut, or hand to a human.")
    if t.get("worktree") and os.path.isdir(t["worktree"]):
        p.git("add", "-A", cwd=t["worktree"], check=False)
        p.git("commit", "--quiet", "-m", f"[{tid}] parked: work in progress", cwd=t["worktree"], check=False)
        p.git("worktree", "remove", "--force", t["worktree"], check=False)
    t.update(status="parked", park_reason=reason, question=q, worktree=None)
    p.save(f"task-park {tid}")
    print(json.dumps({"parked": tid, "question": q}))


def cmd_task_set(p, tid, key, value):
    p.state["tasks"][tid][key] = json.loads(value)
    p.save(f"task-set {tid} {key}")


def cmd_attempt(p, tid, severity):
    if severity not in SEVERITIES:
        sys.exit(f"severity must be one of {SEVERITIES}")
    t = p.state["tasks"][tid]
    t["attempts"][severity] += 1
    limit = int(p.profile()["fix_attempts"][severity])
    p.save(f"attempt {tid} {severity}")
    n = t["attempts"][severity]
    print(f"OK {n}/{limit}" if n <= limit else f"EXHAUSTED {limit}/{limit}")


def cmd_reconcile(p, *_):
    out = []
    for tid, t in p.state["tasks"].items():
        if t["status"] != "in_progress":
            continue
        wt = t.get("worktree")
        info = {"task": tid, "worktree_exists": bool(wt and os.path.isdir(wt))}
        if info["worktree_exists"]:
            info["uncommitted"] = bool(p.git("status", "--porcelain", cwd=wt).stdout.strip())
            info["commits"] = int(p.git("rev-list", "--count", f"{t['base']}..HEAD", cwd=wt).stdout.strip() or 0)
        info["last_results"] = sorted(os.path.basename(f) for f in glob.glob(os.path.join(p.rt, "results", tid, "*.json")))
        out.append(info)
    print(json.dumps({"paused": p.state.get("paused"), "last_step": p.state.get("last_step"), "in_progress": out}, indent=1))


def cmd_result(p, tid, step):
    path = os.path.join(p.rt, "results", tid, f"{step}.json")
    if not os.path.exists(path):
        print(json.dumps({"missing": path}))
        return 1
    r = json.load(open(path))
    findings = r.get("findings", [])
    print(json.dumps({"verdict": r.get("verdict"), "summary": r.get("summary"),
                      "findings": [{k: f.get(k) for k in ("task", "severity", "file", "line", "issue", "fix")} for f in findings]}))
    return 0


def cmd_log(p, agent, task, note=""):
    prof = p.profile()
    model = prof["models"].get({"foreman": "foreman"}.get(agent, ""), None)
    if model is None:
        model = prof["models"]["reviewers"] if agent.startswith(("reviewer", "tester")) else (
            prof["models"]["debug_deep"] if agent == "debugger-deep" else prof["models"]["workers"])
    wave = p.state["tasks"].get(task, {}).get("wave") if task != "-" else None
    with open(os.path.join(p.rt, "usage-log.jsonl"), "a") as f:
        f.write(json.dumps({"at": now(), "profile": prof["name"], "model": model, "agent": agent,
                            "task": None if task == "-" else task, "wave": wave, "note": note}) + "\n")


def cmd_question(p, *text):
    print(json.dumps({"question": p.question(" ".join(text))}))


def cmd_profile(p, *_):
    print(json.dumps(p.profile()))


def cmd_status(p, *_):
    s, prof = p.state, p.profile()
    lines = [f"# Agent-thon status — {now()}", "", f"Profile: **{prof['name']}** · parallel workers: {prof['parallel_workers']} · review: {prof['review_mode']}/{prof['review_scope']}"]
    lock = os.path.join(p.rt, "foreman.lock")
    running = False
    if os.path.exists(lock):
        try:
            os.kill(json.load(open(lock))["pid"], 0)
            running = True
        except (OSError, KeyError, ValueError):
            pass
    if s.get("paused"):
        lines.append(f"\n**PAUSED** ({s['paused']['at']}): {s['paused']['reason']}")
        lines.append("Resume: switch account if needed (/logout → /login), then `run-agent.sh foreman <project> resume`")
    elif not running and any(t["status"] == "in_progress" for t in s["tasks"].values()):
        lines.append("\n**STOPPED** — Foreman not running with tasks in progress (usage limit or crash?). Resume: `run-agent.sh foreman <project> resume`")
    else:
        lines.append(f"\nForeman: {'running' if running else 'not running'}")
    lines += ["", "## Waves", "", "| Wave | Title | Status | Tasks merged | PR |", "|---|---|---|---|---|"]
    for n in sorted(s["waves"], key=int):
        w = s["waves"][n]
        ts = [t for t in s["tasks"].values() if t["wave"] == int(n)]
        done = sum(t["status"] == "merged" for t in ts)
        lines.append(f"| {n} | {w.get('title') or ''} | {w['status']} | {done}/{len(ts)} | {w.get('pr_url') or ''} |")
    active = [(tid, t) for tid, t in s["tasks"].items() if t["status"] in ("in_progress", "parked")]
    if active:
        lines += ["", "## Tasks needing attention or in progress", ""]
        for tid, t in sorted(active):
            extra = f" — {t.get('park_reason')} ({t.get('question')})" if t["status"] == "parked" else f" — step: {t.get('step', 'build')}"
            lines.append(f"- {tid} [{t['status']}] {t['title']}{extra}")
    evals = [n for n, w in s["waves"].items() if w.get("eval_status") == "awaiting_decision"]
    if evals:
        lines += ["", "## AWAITING EVAL DECISION", ""] + [f"- wave {n}: runtime/results/wave-{n}/eval-report.md" for n in evals]
    qpath = os.path.join(p.rt, "questions.md")
    if os.path.exists(qpath):
        open_q = re.findall(r"^## (Q-\d+) .*— OPEN$", open(qpath).read(), re.M)
        if open_q:
            lines += ["", f"## Open questions for the Architect: {', '.join(open_q)}", "(runtime/questions.md; issues labelled foreman-question when shared)"]
    if s.get("plan"):
        lines += ["", f"Plan: {s['plan']['ref']} @ {s['plan']['commit']} (ingested {s['plan']['at']})"]
    lines += ["", f"Last step: {s.get('last_step')} · updated {s.get('updated_at')}"]
    open(os.path.join(p.rt, "status.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


def pr_body(p, n):
    w = p.state["waves"][str(n)]
    footer = p.config().get("git", {}).get("pr_footer", True)
    tasks = {tid: t for tid, t in p.state["tasks"].items() if t["wave"] == int(n)}
    out = [f"## Wave {n}: {w.get('title') or ''}", "", f"**Goal:** {w.get('goal') or ''}", "",
           (f"Built by Agent-thon Foreman · profile `{w.get('profile')}` · " if footer else "") + f"base `{w.get('base')}`", ""]
    if w.get("contracts_synced"):
        out += ["Includes a contracts sync from the released plan (architect-owned folder).", ""]
    out += ["### Tasks", "", "| Task | Title | Builder | Status |", "|---|---|---|---|"]
    for tid, t in sorted(tasks.items()):
        out.append(f"| {tid} | {t['title']} | {t['assigned_to']} | {t['status']} |")
    for step, title in (("review", "Review"), ("integration", "Integration tests"), ("e2e", "E2E tests"), ("eval", "Eval")):
        path = os.path.join(p.rt, "results", f"wave-{n}", f"{step}.json")
        if os.path.exists(path):
            r = json.load(open(path))
            out += ["", f"### {title}: {r.get('verdict')}", "", r.get("summary") or ""]
    gate = os.path.join(p.rt, "results", f"wave-{n}", "gate.json")
    if os.path.exists(gate):
        g = json.load(open(gate))
        out += ["", f"### Gate (final, after syncing main): {g['verdict']}", ""] + [f"- {c['status'].upper()} {c['category']}: `{c['command']}`" for c in g["checks"]]
    known = w.get("known_issues") or []
    if known:
        out += ["", "### Known issues (not fixed within the attempt limits)", ""] + [f"- {k}" for k in known]
    parked = [(tid, t) for tid, t in tasks.items() if t["status"] == "parked"]
    if parked:
        out += ["", "### Parked tasks (not in this PR)", ""] + [f"- {tid}: {t.get('park_reason')}" for tid, t in parked]
    if w.get("eval_required"):
        out += ["", "### Eval decision required", "", "The eval summary is posted as a comment on this PR. Decide via the Architect: **approve**, **approve + follow-ups**, or **fail**. Do not merge before the decision."]
    out += ["", "---", "Merge = deploy. Review behaviour and demo fit; the gates above cover the mechanics."]
    if footer:
        out += ["", "🤖 Generated with [Claude Code](https://claude.com/claude-code)"]
    return "\n".join(out) + "\n"


def cmd_pr_body(p, n):
    print(pr_body(p, n))


def cmd_open_pr(p, n):
    w = p.state["waves"][str(n)]
    branch = w["branch"]
    body_path = os.path.join(p.rt, "results", f"wave-{n}", "pr-body.md")
    os.makedirs(os.path.dirname(body_path), exist_ok=True)
    open(body_path, "w").write(pr_body(p, n))
    if not p.has_remote():
        w.update(status="pr_open", pr_url=None)
        p.save(f"open-pr {n} (no remote)")
        print(json.dumps({"pr": None, "note": "no remote configured — PR body written", "body": body_path}))
        return 0
    p.git("push", "--quiet", "-u", "origin", branch, cwd=p.foreman_wt)
    base = w["base"].replace("origin/", "", 1)
    title = f"Wave {n}: {w.get('title') or ''}".strip()
    existing = subprocess.run(["gh", "pr", "view", branch, "--json", "url", "-q", ".url"], cwd=p.foreman_wt,
                              capture_output=True, text=True)
    if existing.returncode == 0 and existing.stdout.strip():
        url = existing.stdout.strip()
        subprocess.run(["gh", "pr", "edit", branch, "--body-file", body_path], cwd=p.foreman_wt, check=True,
                       capture_output=True, text=True)
    else:
        r = subprocess.run(["gh", "pr", "create", "--base", base, "--head", branch, "--title", title, "--body-file", body_path],
                           cwd=p.foreman_wt, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"gh pr create failed: {r.stderr.strip()}")
        url = r.stdout.strip().splitlines()[-1]
    w.update(status="pr_open", pr_url=url, pr_opened_at=now())
    p.save(f"open-pr {n}")
    print(json.dumps({"pr": url}))
    return 0


COMMANDS = {
    "ingest": cmd_ingest, "wait": cmd_wait, "wave-start": cmd_wave_start, "wave-sync": cmd_wave_sync,
    "wave-set": cmd_wave_set, "open-pr": cmd_open_pr, "pr-body": cmd_pr_body, "ready": cmd_ready,
    "task-start": cmd_task_start, "task-merge": cmd_task_merge, "task-park": cmd_task_park, "task-set": cmd_task_set,
    "fix-start": cmd_fix_start, "fix-merge": cmd_fix_merge, "attempt": cmd_attempt, "reconcile": cmd_reconcile, "result": cmd_result, "log": cmd_log,
    "status": cmd_status, "profile": cmd_profile, "question": cmd_question,
}


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in COMMANDS:
        print(__doc__)
        return 2
    p = Project(sys.argv[1])
    try:
        rc = COMMANDS[sys.argv[2]](p, *sys.argv[3:])
    except TypeError as e:
        print(f"Bad arguments for {sys.argv[2]}: {e}\n\n{__doc__}")
        return 2
    except RuntimeError as e:
        print(f"ERROR {e}")
        return 1
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
