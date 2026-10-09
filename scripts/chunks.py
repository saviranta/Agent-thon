#!/usr/bin/env python3
"""chunks.py — check the architecture split (chunks.json) and generate ownership.yml from it. No LLM.

Usage:
  chunks.py <project> check        validate chunks.json against config.layout, contracts/ and the team
  chunks.py <project> ownership    write ownership.yml from chunks.json (+ contracts_dir → architect)

chunks.json (agent home): {"contracts_status": "draft|frozen", "chunks": [{id, title, paths, owner, reviewers,
purpose, demo_steps, provides, consumes, works_alone_with}]} — template: templates/home/chunks.json.
Exit 0 = ok (warnings allowed), 1 = errors, 2 = usage.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agenthome import contracts_dir, find_home, layout, load_config  # noqa: E402


def static_prefix(glob):
    """Literal leading directories of a glob ('api/routes/**' → 'api/routes')."""
    parts = []
    for seg in glob.split("/"):
        if any(c in seg for c in "*?["):
            break
        parts.append(seg)
    return "/".join(parts)


def load_chunks(home):
    path = os.path.join(home, "chunks.json")
    if not os.path.exists(path):
        raise SystemExit("ERROR chunks.json missing — the Architect writes it in phase 1 (template: templates/home/chunks.json)")
    return json.load(open(path))


def check(home):
    cfg = load_config(home)
    data = load_chunks(home)
    errors, warnings = [], []
    err, warn = errors.append, warnings.append
    folders, _ = layout(cfg)
    cdir = contracts_dir(cfg)
    handles = {m.get("github", "").lstrip("@") for m in cfg.get("team", {}).get("members", [])} - {""}
    contracts_root = os.path.join(home, "contracts")
    contract_files = set()
    for d, _, files in os.walk(contracts_root):
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), contracts_root)
            if not rel.startswith("examples/") and f != ".gitkeep":
                contract_files.add(rel)

    if "FILL_IN" in open(os.path.join(home, "chunks.json")).read():
        err("chunks.json still contains FILL_IN placeholders")
    if not folders:
        err("config.layout.folders is empty — decide the product's top-level folders first")
    if not cdir:
        err("config.contracts_dir is not set (product folder the contracts are published to)")
    elif folders and cdir.split("/")[0] not in folders:
        err(f"contracts_dir '{cdir}' is not inside a layout folder {folders}")
    if data.get("contracts_status") not in ("draft", "frozen"):
        err("contracts_status must be 'draft' or 'frozen'")

    chunks = data.get("chunks", [])
    if not chunks:
        err("no chunks defined")
    ids, providers, consumers, globs = set(), {}, {}, {}
    for c in chunks:
        cid = c.get("id") or "?"
        p = f"{cid}:"
        if cid in ids:
            err(f"{p} duplicate id")
        ids.add(cid)
        owner = c.get("owner", "")
        if owner != "agents" and not re.fullmatch(r"@[A-Za-z0-9-]+", owner or ""):
            err(f"{p} owner must be 'agents' or '@github-handle' (got '{owner}')")
        elif owner.startswith("@") and handles and owner[1:] not in handles:
            warn(f"{p} owner {owner} is not in config.team.members")
        if not c.get("paths"):
            err(f"{p} no paths")
        for g in c.get("paths", []):
            top = g.split("/", 1)[0]
            if folders and top not in folders:
                err(f"{p} path {g} is outside the layout folders {folders}")
            if cdir and (static_prefix(g) == cdir or static_prefix(g).startswith(cdir + "/")):
                err(f"{p} path {g} is inside contracts_dir ({cdir}) — contracts belong to the Architect")
            if g in globs:
                err(f"{p} path {g} is also in chunk {globs[g]}")
            globs[g] = cid
        if not c.get("purpose"):
            warn(f"{p} no purpose")
        if not c.get("works_alone_with"):
            warn(f"{p} works_alone_with is empty — how is it built before the others exist?")
        for k, bucket in (("provides", providers), ("consumes", consumers)):
            for f in c.get(k, []):
                if f not in contract_files:
                    err(f"{p} {k} {f}: no such file in contracts/")
                bucket.setdefault(f, []).append(cid)

    # nested paths across chunks (allowed — most specific wins — but worth a look)
    items = list(globs.items())
    for i, (g1, c1) in enumerate(items):
        for g2, c2 in items[i + 1:]:
            if c1 == c2:
                continue
            a, b = static_prefix(g1), static_prefix(g2)
            if a and b and (a.startswith(b + "/") or b.startswith(a + "/")):
                warn(f"{c1} {g1} and {c2} {g2} are nested — the more specific one wins; make sure that's intended")

    for f, cs in providers.items():
        if len(cs) > 1:
            warn(f"contract {f} provided by several chunks {cs}")
    for f, cs in consumers.items():
        if f not in providers:
            warn(f"contract {f} consumed by {cs} but provided by no chunk (external? say so in its README)")
    for f in sorted(contract_files - set(providers) - set(consumers)):
        if not f.lower().startswith("readme"):
            warn(f"contract {f} is not provided or consumed by any chunk")
    covered = {g.split("/", 1)[0] for g in globs}
    for f in folders:
        if f not in covered:
            warn(f"layout folder {f}/ belongs to no chunk")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    owners = {}
    for c in chunks:
        owners.setdefault(c.get("owner"), []).append(c.get("id"))
    print(f"\nchunks: {len(chunks)} ({', '.join(f'{o}: {len(v)}' for o, v in owners.items())}), "
          f"contracts {data.get('contracts_status')}, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


def write_ownership(home):
    cfg = load_config(home)
    data = load_chunks(home)
    cdir = contracts_dir(cfg)
    lines = ["# ownership.yml — GENERATED from chunks.json by chunks.py (edit chunks.json, then run chunks.py <project> ownership).",
             "# Paths are relative to the product repo. Most specific match wins.",
             "# owner: agents | architect | @github-handle   (agents = built by the Foreman's workers)", "", "areas:"]
    for c in data.get("chunks", []):
        for g in c.get("paths", []):
            lines.append(f'  - path: "{g}"')
            lines.append(f'    owner: {c.get("owner")}')
            if c.get("reviewers"):
                lines.append(f'    reviewers: [{", ".join(json.dumps(r) for r in c["reviewers"])}]')
            lines.append(f'    change_rule: "chunk {c.get("id")}: {c.get("title", "")}"')
    if cdir:
        lines += [f'  - path: "{cdir}/**"', "    owner: architect",
                  '    change_rule: "Published from the agent home by contracts.py; change via the Architect"']
    if len(lines) == 5:
        lines[-1] = "areas: []"
    open(os.path.join(home, "ownership.yml"), "w").write("\n".join(lines) + "\n")
    print(f"ownership.yml written ({sum(len(c.get('paths', [])) for c in data.get('chunks', []))} chunk paths"
          f"{', contracts ' + cdir if cdir else ''})")
    return 0


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in ("check", "ownership"):
        print(__doc__)
        return 2
    home = find_home(sys.argv[1])
    return check(home) if sys.argv[2] == "check" else write_ownership(home)


if __name__ == "__main__":
    sys.exit(main())
