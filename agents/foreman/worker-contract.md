# Worker contract (applies to every builder, fixer, debugger, reviewer and tester)

The Foreman dispatches you with: your role file, the project root, a **working directory** (a git worktree), the task id or wave number, and the paths you need. It reads only the result file you write — keep your final chat reply to one line.

## Where you work
- Work **only inside the working directory you were given**. Use absolute paths. For shell commands, `cd <working directory>` first.
- Never touch the user's main checkout, other worktrees, `main`, or `contracts/` (read-only), and never edit `.agentthon/` except where your role says so.
- Never read or write `.env*` or `secrets/`. Never push, merge, rebase, or open PRs — the Foreman does that.
- Never call real external AI providers in tests; use the project's fake adapter.

## Before you finish
- Builders and fixers: run the gate yourself and fix what you can:
  `bash $AGENTTHON_TOOLKIT/scripts/gate.sh <working directory> --task <task-id> --base <base> --results <project>/.agentthon/runtime/results/<task-id>`
- Commit your work in the working directory: `git add -A && git commit -m "[<task-id>] <short message>"`.

## Result file (required)
Write JSON to `<project>/.agentthon/runtime/results/<id>/<step>.json`, where `<id>` is the task id (or `wave-N` for wave-level work) and `<step>` is given by the Foreman (e.g. `build`, `fix-2`, `review`, `review-security`, `integration`, `e2e`, `debug-quick`).

```json
{
  "role": "builder-api",
  "id": "task-007",
  "step": "build",
  "verdict": "PASS | NEEDS_CHANGES | FAIL | BLOCKED",
  "summary": "one or two sentences",
  "files_changed": ["path", "..."],
  "findings": [
    {
      "task": "task-007",
      "severity": "critical | standard | polish",
      "category": "correctness | security | domain | ui | conventions | test | contract",
      "file": "path",
      "line": 42,
      "issue": "what is wrong, concretely",
      "fix": "what to change"
    }
  ],
  "blocked_reason": "only when verdict is BLOCKED: what is missing or ambiguous, and what decision is needed",
  "notes": "anything the Foreman must know (optional, short)"
}
```

Verdict meanings:
- **PASS** — done / approved / tests pass.
- **NEEDS_CHANGES** — reviewers: specific findings to fix. Builders: never use this.
- **FAIL** — tests fail or work could not be completed for a technical reason; findings explain why.
- **BLOCKED** — cannot proceed without a human or Architect decision (ambiguous spec, contract gap, needed file owned by someone else). Do not guess around a contract gap.

Severity guide: **critical** = security, data loss/corruption, broken core demo flow, fabricated domain information shown to users. **standard** = incorrect behaviour, failing test, contract mismatch. **polish** = style, naming, minor UX.

Final chat reply: `<verdict> — <result file path>`.
