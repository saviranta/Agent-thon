"""agenthome.py — locate an Agent-thon project's two folders (standard library only).

  <repo>/          product repository — product code only
  <repo>-agents/   agent home — config, chunks, contracts source, ownership, claims, waves, artifacts, runtime/

The Foreman and its workers read the *released* plan from runtime/plan (a detached worktree of the agent
home at its main branch, refreshed by `foreman.py ingest`); the Architect works in the agent home itself.
"""

import json
import os
import re
import subprocess

HOME_SUFFIX = "-agents"


def is_home(path):
    p = os.path.join(path, "config.json")
    if not os.path.isfile(p):
        return False
    try:
        return json.load(open(p)).get("agentthon_home") is True
    except ValueError:
        return False


def find_home(path):
    """Agent home for a path that is either the agent home or the product repo next to it."""
    real = os.path.realpath(path)
    if is_home(real):
        return real
    if is_home(real + HOME_SUFFIX):
        return real + HOME_SUFFIX
    raise SystemExit(f"Not an Agent-thon project: {real} (no agent home {os.path.basename(real)}{HOME_SUFFIX}/ next to it)")


def load_config(d):
    return json.load(open(os.path.join(d, "config.json")))


def _origin(path):
    r = subprocess.run(["git", "-C", path, "remote", "get-url", "origin"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def repo_of(home):
    """Product repo: runtime/local.json repo_path → config.repo_path → sibling whose origin is config.git.github_repo."""
    rel = ""
    local = os.path.join(home, "runtime", "local.json")
    if os.path.exists(local):
        rel = json.load(open(local)).get("repo_path") or ""
    cfg = load_config(home)
    rel = rel or cfg.get("repo_path") or ""
    if rel:
        cand = os.path.realpath(os.path.join(home, rel))
        if os.path.isdir(cand):
            return cand
    gh = cfg.get("git", {}).get("github_repo")
    if gh:
        parent = os.path.dirname(home)
        for name in sorted(os.listdir(parent)):
            cand = os.path.join(parent, name)
            if cand != home and os.path.isdir(cand) and re.search(rf"github\.com[:/]{re.escape(gh)}(\.git)?$", _origin(cand)):
                return os.path.realpath(cand)
    raise SystemExit(f"Product repo not found for {home} (repo_path '{rel}'); set repo_path in runtime/local.json")


def plan_dir(home):
    """The released plan if the Foreman has checked it out, else the agent home's working copy."""
    plan = os.path.join(home, "runtime", "plan")
    return plan if os.path.isfile(os.path.join(plan, "config.json")) else home


def layout(cfg):
    lay = cfg.get("layout", {}) or {}
    return [f.strip("/") for f in lay.get("folders", []) or []], lay.get("root_files", []) or []


def in_layout(cfg, path):
    """True if a product-repo path is inside a layout folder or is an allowed root file. No layout set → True."""
    folders, root_files = layout(cfg)
    if not folders:
        return True
    if "/" not in path:
        return path in root_files
    return path.split("/", 1)[0] in folders


def contracts_dir(cfg):
    return (cfg.get("contracts_dir") or "").strip("/")
