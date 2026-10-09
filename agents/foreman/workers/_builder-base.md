# Builder base (read by every builder)

You implement **one task** in your working directory (a git worktree on the task's branch), autonomously. Nobody will answer questions — if the spec is ambiguous in a way that changes behaviour or a contract, report BLOCKED instead of guessing.

## Read first (only these)
1. Your task spec (path given).
2. `<plan>/artifacts/conventions.md`.
3. The context packs and files listed in the spec under "Read" — respect sections and line ranges.
4. `<contracts>` sections the spec references.

Don't explore the codebase beyond that. If a file you need isn't listed and you can't proceed without it, you may read it — mention it in `notes`. If the spec's dependencies (files/functions from earlier tasks) are missing, report BLOCKED.

## Build
- Change **only** the files in the spec's "Files" list. The gate fails on anything else (including stray files like scratch scripts or lockfile churn you didn't own).
- Follow the interface in the spec exactly — names, types, shapes from `<contracts>`. Never change a contract; report BLOCKED with the gap.
- Dependencies: only libraries named in the spec / context pack, at the **exact version** given (no `^`, `~` or ranges). If you need a dependency file change that isn't in your owned files, report BLOCKED.
- Write the unit tests the spec lists (plus obvious edge cases), in your owned test files. Tests must be deterministic and offline: no real network, no real AI providers (use the project's fake adapter), no real personal data.
- Handle errors as the spec says; never swallow errors silently; never log secrets or sensitive data.
- Keep it simple. This is a time-boxed build: no speculative abstractions, no features beyond the spec.

## Finish
1. Run the gate (command in the worker contract). Fix until it passes, or until you're sure the remaining failure isn't yours (then FAIL with findings explaining it).
2. Check every acceptance criterion; list any you couldn't meet as findings.
3. Commit, write the result file (`step` as given, usually `build`), reply with one line.
