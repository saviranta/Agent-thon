#!/usr/bin/env python3
"""contracts.py — check, compare and publish the contracts between chunks. No LLM.

Source of truth: contracts/ in the agent home (+ contracts/examples/<name>/*.json, one folder per schema).
Published copy: config.contracts_dir in the product repo (architect-owned; workers never edit it).

Usage:
  contracts.py <project> check                 parse every contract; check cross-file $refs; validate examples
                                               against their schema (needs the jsonschema package; else warns)
  contracts.py <project> status                agent home contracts vs the product repo's main (published?)
  contracts.py <project> publish [message]     open a contracts PR in the product repo (branch config.git.contracts_branch_prefix…)
  contracts.py <project> sync <worktree> [msg] copy the released plan's contracts into a product worktree and commit (Foreman)

Exit 0 = ok, 1 = errors / differences (status), 2 = usage.
"""

import datetime
import filecmp
import glob
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agenthome import contracts_dir, find_home, load_config, plan_dir, repo_of  # noqa: E402

SKIP = {".gitkeep", ".DS_Store"}
TOOLKIT_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv", "bin", "python")


def use_toolkit_python():
    """Re-run under the toolkit's venv (setup-toolkit.sh) when jsonschema isn't importable here."""
    try:
        import jsonschema  # noqa: F401
        return
    except ImportError:
        pass
    venv = os.path.dirname(os.path.dirname(TOOLKIT_PY))
    if os.path.exists(TOOLKIT_PY) and os.path.realpath(sys.prefix) != os.path.realpath(venv) \
            and not os.environ.get("AGENTTHON_REEXEC"):
        os.environ["AGENTTHON_REEXEC"] = "1"
        os.execv(TOOLKIT_PY, [TOOLKIT_PY, *sys.argv])


def git(cwd, *args, check=True):
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r


def source_files(src):
    out = {}
    for d, _, files in os.walk(src):
        for f in files:
            if f not in SKIP:
                full = os.path.join(d, f)
                out[os.path.relpath(full, src)] = full
    return out


# ── check ──

def cmd_check(home):
    root = os.path.join(home, "contracts")
    files = source_files(root)
    errors, warnings, parsed = [], [], {}
    if not files:
        print("contracts: none yet (contracts/ is empty)")
        return 0
    for rel, full in sorted(files.items()):
        if rel.endswith(".json"):
            try:
                parsed[rel] = json.load(open(full))
            except ValueError as e:
                errors.append(f"{rel}: invalid JSON — {e}")
        elif rel.endswith((".yaml", ".yml")):
            try:
                import yaml  # noqa: F401
                yaml.safe_load(open(full))
            except ImportError:
                pass
            except Exception as e:  # noqa: BLE001
                errors.append(f"{rel}: invalid YAML — {e}")

    def refs(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str):
                    yield v
                else:
                    yield from refs(v)
        elif isinstance(node, list):
            for v in node:
                yield from refs(v)

    schemas = {rel: s for rel, s in parsed.items() if rel.endswith(".schema.json") and not rel.startswith("examples/")}
    for rel, s in schemas.items():
        for r in refs(s):
            target = r.split("#", 1)[0]
            if target and not target.startswith(("http://", "https://")):
                if not os.path.exists(os.path.join(root, os.path.dirname(rel), target)):
                    errors.append(f"{rel}: $ref {r} points to a missing file")

    try:
        import jsonschema
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT202012
        have_validator = True
    except ImportError:
        have_validator = False
        warnings.append("jsonschema not available — examples were NOT validated. Run once: bash $AGENTTHON_TOOLKIT/scripts/setup-toolkit.sh")

    if have_validator:
        registry = Registry()
        for rel, s in schemas.items():
            res = Resource.from_contents(s, default_specification=DRAFT202012)
            registry = registry.with_resource(rel, res)
            if isinstance(s, dict) and s.get("$id"):
                registry = registry.with_resource(s["$id"], res)
    for rel, s in sorted(schemas.items()):
        stem = os.path.basename(rel)[: -len(".schema.json")]
        examples = sorted(glob.glob(os.path.join(root, "examples", stem, "*.json")))
        if not examples:
            warnings.append(f"{rel}: no examples in contracts/examples/{stem}/ — add at least one valid example")
            continue
        if not have_validator:
            continue
        try:
            cls = jsonschema.validators.validator_for(s)
            cls.check_schema(s)
            validator = cls(s, registry=registry)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{rel}: not a valid JSON Schema — {e}")
            continue
        for ex in examples:
            try:
                inst = json.load(open(ex))
            except ValueError as e:
                errors.append(f"{os.path.relpath(ex, root)}: invalid JSON — {e}")
                continue
            errs = sorted(validator.iter_errors(inst), key=lambda e: list(e.path))
            for e in errs[:3]:
                loc = "/".join(map(str, e.path)) or "(root)"
                errors.append(f"{os.path.relpath(ex, root)} vs {rel}: {loc}: {e.message}")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\ncontracts: {len(files)} files, {len(schemas)} schemas, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


# ── status ──

def main_ref(repo, cfg):
    main = cfg.get("git", {}).get("main_branch", "main")
    if git(repo, "remote", "get-url", "origin", check=False).returncode == 0:
        git(repo, "fetch", "--quiet", "origin", check=False)
        return f"origin/{main}"
    return main


def compare(home, src_dir=None):
    """Differences between contracts source and the product's main: {added, changed, removed, ref}."""
    cfg = load_config(home)
    cdir = contracts_dir(cfg)
    if not cdir:
        raise SystemExit("config.contracts_dir is not set")
    repo = repo_of(home)
    ref = main_ref(repo, cfg)
    src = source_files(src_dir or os.path.join(home, "contracts"))
    listed = git(repo, "ls-tree", "-r", "--name-only", ref, "--", cdir, check=False).stdout.split()
    published = {os.path.relpath(p, cdir): p for p in listed if os.path.basename(p) not in SKIP}
    added, changed = [], []
    for rel, full in sorted(src.items()):
        if rel not in published:
            added.append(rel)
            continue
        shown = subprocess.run(["git", "-C", repo, "show", f"{ref}:{published[rel]}"], capture_output=True)
        if shown.stdout != open(full, "rb").read():
            changed.append(rel)
    removed = sorted(set(published) - set(src))
    return {"ref": ref, "contracts_dir": cdir, "added": added, "changed": changed, "removed": removed}


def cmd_status(home):
    d = compare(home)
    in_sync = not (d["added"] or d["changed"] or d["removed"])
    print(json.dumps(dict(d, in_sync=in_sync)))
    return 0 if in_sync else 1


# ── sync / publish ──

def copy_into(src_root, worktree, cdir):
    """Make <worktree>/<cdir> an exact copy of src_root (minus SKIP). Returns True if anything changed."""
    dst_root = os.path.join(worktree, cdir)
    src = source_files(src_root)
    dst = source_files(dst_root) if os.path.isdir(dst_root) else {}
    changed = False
    for rel, full in src.items():
        target = os.path.join(dst_root, rel)
        if rel not in dst or not filecmp.cmp(full, target, shallow=False):
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(full, target)
            changed = True
    for rel in set(dst) - set(src):
        os.remove(os.path.join(dst_root, rel))
        changed = True
    return changed


def commit_all(worktree, message):
    git(worktree, "add", "-A")
    if git(worktree, "diff", "--cached", "--quiet", check=False).returncode == 0:
        return False
    git(worktree, "commit", "--quiet", "-m", message)
    return True


def cmd_sync(home, worktree, message="contracts: sync from the released plan"):
    plan = plan_dir(home)
    cdir = contracts_dir(load_config(plan))
    if not cdir:
        print(json.dumps({"synced": False, "note": "contracts_dir not set"}))
        return 0
    worktree = os.path.abspath(worktree)
    changed = copy_into(os.path.join(plan, "contracts"), worktree, cdir)
    # only the contracts dir may be committed here
    if changed:
        git(worktree, "add", "-A", "--", cdir)
        if git(worktree, "diff", "--cached", "--quiet", check=False).returncode != 0:
            git(worktree, "commit", "--quiet", "-m", message, "--", cdir)
    print(json.dumps({"synced": True, "changed": changed, "contracts_dir": cdir}))
    return 0


def cmd_publish(home, message="update"):
    cfg = load_config(home)
    cdir = contracts_dir(cfg)
    if not cdir:
        raise SystemExit("config.contracts_dir is not set")
    if git(home, "status", "--porcelain", "--", "contracts", "chunks.json").stdout.strip():
        raise SystemExit("Commit contracts/ and chunks.json in the agent home first (the published copy must match a recorded version)")
    if cmd_check(home) != 0:
        raise SystemExit("Fix the contract errors above before publishing")
    diff = compare(home)
    if not (diff["added"] or diff["changed"] or diff["removed"]):
        print(json.dumps({"published": False, "note": "product main already has these contracts"}))
        return 0
    repo = repo_of(home)
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M")
    branch = cfg.get("git", {}).get("contracts_branch_prefix", "contracts/") + stamp
    wt = os.path.join(home, "runtime", "worktrees", "contracts-publish")
    if os.path.isdir(wt):
        git(repo, "worktree", "remove", "--force", wt)
    git(repo, "worktree", "add", "--quiet", "-b", branch, wt, diff["ref"])
    try:
        copy_into(os.path.join(home, "contracts"), wt, cdir)
        commit_all(wt, f"Contracts: {message}")
        has_remote = git(repo, "remote", "get-url", "origin", check=False).returncode == 0
        url = None
        if has_remote:
            git(wt, "push", "--quiet", "-u", "origin", branch)
            chunks = json.load(open(os.path.join(home, "chunks.json"))).get("chunks", []) if os.path.exists(os.path.join(home, "chunks.json")) else []
            touched = set(diff["added"] + diff["changed"] + diff["removed"])
            owners = sorted({c.get("owner") for c in chunks if touched & set(c.get("provides", []) + c.get("consumes", []))})
            body = [f"Contracts published from the agent home ({message}).", "",
                    f"Folder: `{cdir}/` — architect-owned; change via the Architect, never in a feature PR.", ""]
            for k in ("added", "changed", "removed"):
                if diff[k]:
                    body.append(f"**{k.capitalize()}:** " + ", ".join(f"`{f}`" for f in diff[k]))
            if owners:
                body += ["", "Affected chunk owners: " + ", ".join(owners)]
            if cfg.get("git", {}).get("pr_footer", True):
                body += ["", "🤖 Generated with [Claude Code](https://claude.com/claude-code)"]
            r = subprocess.run(["gh", "pr", "create", "--base", cfg.get("git", {}).get("main_branch", "main"), "--head", branch,
                                "--title", f"Contracts: {message}", "--body", "\n".join(body) + "\n"],
                               cwd=wt, capture_output=True, text=True)
            if r.returncode != 0:
                raise SystemExit(f"pushed {branch}, but gh pr create failed: {r.stderr.strip()}")
            url = r.stdout.strip().splitlines()[-1]
        print(json.dumps({"published": True, "branch": branch, "pr": url, **{k: diff[k] for k in ("added", "changed", "removed")},
                          "note": None if has_remote else "no remote — branch created locally; merge it into main"}))
    finally:
        git(repo, "worktree", "remove", "--force", wt, check=False)
    return 0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    home = find_home(sys.argv[1])
    cmd, rest = sys.argv[2], sys.argv[3:]
    if cmd in ("check", "publish"):
        use_toolkit_python()
    if cmd == "check":
        return cmd_check(home)
    if cmd == "status":
        return cmd_status(home)
    if cmd == "publish":
        return cmd_publish(home, " ".join(rest) or "update")
    if cmd == "sync" and rest:
        return cmd_sync(home, rest[0], " ".join(rest[1:]) or "contracts: sync from the released plan")
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
