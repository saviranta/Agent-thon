# Playbook: library discovery (GitHits)

Used by the Architect (all capabilities) and the Prototyper (UI kit, icons, charts, motion, fonts). Goal: pick libraries that **actually work today** for this data and this stack — the best fit for a time-boxed build, not the most powerful option.

1. **Find candidates** — GitHits `search` / `get_example` for working code that does the capability in the chosen language and framework; add well-known alternatives you know of (including "no library — the standard library or a few lines of code").
2. **Check health** — `pkg_info` (latest version, maintenance, licence), `pkg_vulns` (known vulnerabilities), `pkg_deps` (dependency weight — heavy installs slow every fresh worktree and container), `pkg_changelog` for recent breaking changes (major versions that examples online don't match yet are a common trap).
3. **Prove it works** — prefer candidates with a working example (`get_example`, `quick_start`) close to our use; note the example's source so builders can follow it.
4. **Fit** — to the data (format, language, size) for data libraries; to the frontend framework, styling approach and the chosen visual direction for UI libraries. A popular library that doesn't fit is out.
5. **Decide** — pin the **exact version** (no `^`/`~`).

If GitHits is unavailable, say so, fall back to your own knowledge, and mark those choices "unverified".

Record each decision (Architect: `artifacts/architecture.md` → Library decisions; Prototyper: `artifacts/ui/design-system.md` → Libraries):

```markdown
### <capability>
- Candidates: <name@version — one line each, source: GitHits | knowledge>
- Checks: <licence, vulns, deps weight, maintenance, fit>
- Decision: <name@exact-version> — <reason>; rejected: <name — why>
- Working example: <link/path from GitHits, if any>
```
Add the chosen libraries, exact versions and example references to the relevant context pack so builders use them the same way.
