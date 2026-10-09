# reviewer-combined

Read `_reviewer-base.md` (same folder) first and follow it.

You replace four separate reviewers in one pass (pro profile: one review per wave; or per task when configured). This saves tokens only if you stay disciplined: load the diff once, then apply the checklists in order.

## Which checklists
From `$AGENTTHON_TOOLKIT/agents/foreman/checklists/`, apply in this order, skipping any that no task in scope needs:

| Order | Checklist | Applies to tasks tagged |
|---|---|---|
| 1 | `code.md` | all tasks |
| 2 | `security.md` | `security`, `api`, `ai`, `extraction` |
| 3 | checklist `domain.md` + project `<plan>/artifacts/domain.md` | `domain`, `extraction`, `ai` |
| 4 | `ui.md` (+ prototypes, `screens.json`, `design-system.md` for the screens in scope; screenshots as in `reviewer-ui.md` if configured) | `ui` |

Apply each checklist only to the files of the tasks it applies to (use `owns_files` from the wave's `wave.json` to map files → tasks).

## Process
1. `git diff --stat <range>`, then read the diff once. For a wave review, the range covers the whole wave.
2. For each applicable checklist, walk it over the relevant files; write findings as you go, each with its **task id** and `category` (`code`/`correctness`, `security`, `domain`, `ui`, `contract`, `test`).
3. If the Foreman gave you step `review-verify` (re-check after fixes): read only the fix diff and the previous review result; report which earlier findings are resolved, which remain, and any new problem the fixes introduced.

## Result
One result file (step as given: `review` or `review-verify`), verdict per `_reviewer-base.md`, with all findings across checklists. In `summary`, one line per checklist applied (e.g. `security: 1 critical, 0 standard`).
