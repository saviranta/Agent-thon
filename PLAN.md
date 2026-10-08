# Agent-thon — Plan

A project-agnostic multi-agent coding toolkit for hackathons and short builds, derived from Agents-max.
The team converses with two agents (Architect, Prototyper); an autonomous Foreman dispatches builders, reviewers and testers to build, review and test task waves without oversight, and opens PRs to `main`.

**Scope of Agent-thon:** coding only. Whatever the built app does at runtime (including calling its own LLM APIs) is configured in the app and its deploy environment, not in Agent-thon.

**No project specifics in the toolkit.** Stack, libraries, data formats, domain rules and schemas are decided per project by the Architect with the team and stored in that project's `.agentthon/`. The toolkit ships methods, checklists and playbooks — not choices.

---

## 1. Principles

- Review and testing are never skipped — profiles change batching and frequency, not coverage.
- Deterministic tools before LLMs (lint, types, tests cost no tokens).
- Foreman never asks the user; it parks and writes to `questions.md`. Only exception: profile question on `resume`.
- Every step is checkpointed to disk; any session can stop and resume.
- Agents are scoped to one project at a time.
- Nothing reaches `main` without a PR. Every path has a defined owner.

---

## 2. Toolkit and project layout

```
~/ClaudeFolder/Agent-thon/                 ← toolkit (shared, never modified by agents at runtime)
  agents/     architect/ prototyper/ foreman/ (sub-agents, checklists, templates)
  playbooks/  text-to-structured.md, eval-design.md, deploy-targets.md, ...
  scripts/    run-agent.sh, gate.sh, wave-ingest, wait-and-resume.sh, validate.sh, ownership-check.sh
  skills/     agentthon-init
  templates/  config.json, settings.json, state.json, wave.json, task-spec.md,
              ownership.yml, TEAM.md, pull_request_template.md, ci.yml

~/ClaudeFolder/ClaudeProjects/<Project>/
  .agentthon/            ← committed, shared with the team
    config.json        shared default profile, stack checks, deploy target, hackathon times
    questions.md       Foreman → Architect/team
    requests.md        teammates → Architect (alternative to `architect` issues)
    claims.md          who is working where
    ownership.yml      folder-level ownership (source of truth)
    runtime/           ← gitignored, local to each machine
      local.json       machine-local profile override (switching accounts doesn't touch shared config)
      state.json       checkpoint (task status, gate step, fix counters, wave pointer, pause)
      status.md        one-screen status (Haiku)
      usage-log.jsonl  agent invocations per wave
      foreman.lock     one Foreman per project (pid-based; stale locks taken over)
      checkpoints/     state snapshots
    artifacts/         brief, ui-spec, wireframes, architecture, contracts, domain brief,
                       domain checklist, context packs, waves, task-specs
    evals/             golden set, eval-wave-N.md reports + decisions
  .claude/settings.json  allowlist + deny rules, scoped to this project
  .github/CODEOWNERS     generated from ownership.yml
  .github/pull_request_template.md, .github/workflows/ci.yml
  .github/copilot-instructions.md  generated (§5.5)
  AGENTS.md              generated — read by Codex and other AI coders (§5.5)
  CLAUDE.md              generated — thin pointer for Claude Code users outside Agent-thon
  .pre-commit-config.yaml  optional local checks, same as CI
  TEAM.md                shared working practices
  <app code — structure decided by Architect>
```

- `/agentthon-init <Project>` creates the folder, git repo (with GitHub remote), `.agentthon/`, settings, TEAM.md, PR template, CI workflow and empty ownership.yml.
- `run-agent.sh <agent> <project-path>` refuses to start without `.agentthon/`, starts Claude Code inside the project with the model from the active profile.
- Project settings deny writes outside the project folder.
- `foreman.lock` blocks a second Foreman on the same project; `foreman resume` takes over a stale lock.

---

## 3. Profiles (the switch)

`.agentthon/config.json`:

```json
{
  "profile": "pro",
  "profiles": {
    "pro": {
      "models":       { "interactive": "sonnet", "foreman": "sonnet", "workers": "sonnet",
                        "reviewers": "sonnet", "debug_deep": "sonnet", "status": "haiku" },
      "parallel_workers": 1,
      "review_mode":  "combined",
      "review_scope": "wave",
      "fix_attempts": { "critical": 3, "standard": 2, "polish": 1 },
      "e2e_scope":    "wave",
      "eval_scope":   "milestone"
    },
    "max": {
      "models":       { "interactive": "opus", "foreman": "opus", "workers": "sonnet",
                        "reviewers": "sonnet", "debug_deep": "opus", "status": "haiku" },
      "parallel_workers": 3,
      "review_mode":  "separate",
      "review_scope": "task",
      "fix_attempts": { "critical": 5, "standard": 3, "polish": 2 },
      "e2e_scope":    "wave",
      "eval_scope":   "wave"
    }
  },
  "overflow": { "mode": "switch-account" },
  "checks": {
    "_comment": "Filled by Architect once the stack is chosen; gate.sh runs these",
    "lint": [], "types": [], "unit": [], "e2e": []
  },
  "deploy": {
    "_comment": "Filled by Architect; target + services; deploys happen from main",
    "target": null,
    "services": [],
    "health_checks": []
  },
  "hackathon": { "start": null, "end": null, "demo_length_minutes": 3 }
}
```

- Foreman reads the profile at the start of every wave → switching mid-event works.
- Model aliases (`opus` / `sonnet` / `haiku`) everywhere — no pinned model IDs.
- `gate.sh` is stack-agnostic: it runs whatever commands `checks` lists.

| | **pro ($20)** | **max ($100)** |
|---|---|---|
| Architect / Prototyper | Sonnet (Opus if available and chosen) | Opus |
| Foreman | Sonnet, sequential | Opus, ≤3 parallel |
| Builders | Sonnet ×1 | Sonnet ×3 |
| Static gate (`gate.sh`) | every task | every task |
| Unit tests | every task | every task |
| LLM review | one combined reviewer per wave (all checklists, wave diff) | separate reviewers per task, tag-routed, parallel |
| Contract tests | after each merge to wave branch | after each merge to wave branch |
| Integration + e2e | per wave | per wave |
| Eval | at milestones | per wave |
| debugger-deep | Sonnet, 2 iterations | Opus, 3 iterations |
| Fix attempts (C/S/P) | 3 / 2 / 1 | 5 / 3 / 2 |

Combined reviewer (pro) runs checklists in order code → security → domain → UI, skips those not relevant to any task in the wave, returns one JSON verdict with per-task findings.

---

## 4. Agents

### Interactive (team converses)

**Architect**
- Starts every project with **Brief & Challenge** (session 0, §4a).
- Decides with the team: stack, libraries, data handling, deploy target — and records the reasoning in `architecture.md`. Fills `config.checks` and `config.deploy`.
- Writes per-project domain artifacts: `domain-brief.md` (data, rules, constraints) and `domain-checklist.md` (used by the domain reviewer).
- Maintains `ownership.yml` with the team (§5) and regenerates CODEOWNERS.
- Sub-agents: task-decomposer, graph-checker (file overlaps, deps, every impl task has tests, every UI task references a wireframe, **every `owns_files` path is agent-owned in ownership.yml**).
- Outputs: `architecture.md`, `contracts/` (only Architect writes), `conventions.md` (incl. exact-version rule: no `^`/`~`), context packs (≤2k tokens each), `waves/wave-N.json` + `task-specs/`.
- Releases waves on "release wave N": commits wave, specs, contract/ownership/UI changes on `plan/wave-N` and opens a PR. **Merging the plan PR releases the wave**; the Foreman ingests waves from `main`. Designs wave N+1 while N builds.
- Wave validation is deterministic: `scripts/check-wave.py` (overlaps, deps, ownership, claims, specs have tests/criteria, UI tasks have a frozen UI) — no LLM graph-checker.
- At the start of every turn reads `questions.md`, pending evals, open PRs and `architect`-labelled issues / `requests.md`; presents them.
- Regenerates AI-coder instruction files (§5.5) whenever conventions, ownership or contracts change.
- Any team member can talk to the Architect; requests from teammates go through the same brief/challenge rules.

**Prototyper**
- Reads `brief.md` before designing; challenges any screen that doesn't serve the demo script (one round, team decides, logged).
- Sub-agents: wireframer, flow-mapper (Sonnet). Absorbs ux-designer (design tokens).
- Outputs: `ui-spec.md`, `wireframes/*.html` (clickable), `design-tokens.md`, `screens.json`.
- Gate: "UI frozen for wave N".

### 4a. Architect — Brief & Challenge (session 0)

**Interview** (before any design):
- Problem, for whom, why it matters.
- Judging criteria and demo audience; what the jury should remember after the demo.
- Data actually available: source, format, language, volume, sensitivity, and whether it may be sent to external APIs.
- Hackathon rules (pre-built code allowed? AI disclosure? provided datasets?).
- Team members, skills, realistic hours, who wants to own what.

**Challenge** (hackathon lens):
- **Demo-path test** — every feature must appear in the demo script, otherwise it goes on the cut list.
- **Capacity check** — scope vs. what the active profile + team can build in the remaining time; states explicitly what won't fit.
- **Risk check** — technical feasibility in the time available, data quality/language fit of candidate tools, output fragility, domain over-claiming, whether the data demonstrates the point.
- **Pre-mortem** — "It's demo time and it failed. Why?" Top 3 reasons + mitigations.
- **Counter-proposals** — every challenge comes with a reason and a simpler alternative.

**Rules:** one round of challenge per point, then the team decides; recorded in the decision log. No reopening settled decisions unless new information appears. Uses `hackathon.start/end` to reason about remaining time.

**Output:** `artifacts/brief.md` — purpose, judging criteria, demo script, scope in/out, cut list, assumptions, data constraints, pre-mortem, decision log. Re-checked on every wave release and scope addition.

### Autonomous

**Foreman** (orchestrator)
- Ingests waves, dispatches batches, runs gates, merges task branches into the wave branch, opens the wave PR to `main`, writes `status.md`.
- Before each wave and before opening a PR: merges latest `main` into the wave branch, re-runs gates.
- Never asks; ambiguity → park + `questions.md`.
- Reads only status JSON and verdicts.
- Never writes outside agent-owned paths (enforced by `ownership-check.sh` in the gate).

**Builders** (Sonnet; each writes and runs its own unit tests)

| Agent | Scope |
|---|---|
| builder-api | backend endpoints, file handling, storage |
| builder-extraction | turning unstructured text/documents into structured data, following `playbooks/text-to-structured.md` and the project's domain brief |
| builder-ai-integration | code for the app's runtime LLM calls: provider-agnostic adapter, prompts, structured-output validation, provenance checks |
| builder-ui | UI components from wireframes + tokens |
| builder-composer | wiring UI to API |
| builder-infra | containers, deploy config, env vars, CI |
| bug-fixer, debugger-quick → debugger-deep | fix cycles |

**Static gate** — `gate.sh`: runs `config.checks` + `ownership-check.sh` per task worktree. Tool output → bug-fixer. Reviewers run only when green.

**Reviewers** (Sonnet; diff-scoped; separate on max, combined on pro)

| Checklist | When | Source |
|---|---|---|
| code | every task | toolkit: correctness, conventions, contract compliance |
| security | backend/file/LLM tasks | toolkit: input handling, secrets, prompt injection from user-supplied content, sensitive data in logs |
| domain | tasks tagged `domain` / `extraction` / `ai` | **project's `domain-checklist.md`** written by Architect |
| ui | UI tasks | toolkit: wireframe + tokens, a11y basics, empty/error/loading states |

**Testers** (Sonnet)

| Agent | When | What |
|---|---|---|
| tester-contract | after each merge to wave branch | API matches `contracts/` |
| tester-integration | end of wave | end-to-end data flow through the backend |
| tester-e2e | end of wave | browser flows from `screens.json` / demo script |
| tester-eval | per profile | golden set; see §7 |
| smoke-deploy | after main is deployed | `config.deploy.health_checks` + one core flow |

Tests use a fake LLM adapter with recorded responses — deterministic, no runtime API calls. Only the eval calls the real runtime provider, via `run-eval.sh` which loads the key itself (agents never see secret values).

**Patcher** (kept from Agents-max) for small changes; works on its own branch + PR like everyone else.

---

## 5. Team collaboration: branches, PRs, ownership

### 5.1 Branches

| Branch | Who | Purpose |
|---|---|---|
| `main` | nobody directly | protected; deployable; deploy target deploys from here |
| `agentthon/wave-N` | Foreman | integration branch for wave N |
| `agentthon/task-NNN` | builders (worktrees) | one per task, merged into the wave branch by Foreman |
| `<name>/<topic>` | humans | e.g. `anna/timeline-polish` |
| `patch/<topic>` | Patcher | small changes |

- `main` branch protection: PR required, CI (`gate.sh`) must pass, ≥1 approval from a CODEOWNER of touched paths, no direct pushes (also denied in agent settings).
- Merges to `main` are always done by a human. Merge = deploy.

### 5.2 Pull requests

- **Agent wave PR** (opened by Foreman after all gates pass): description lists tasks, files, gate results, reviewer verdict summary, e2e result and — where scheduled — the eval report with its recommendation. The eval decision (approve / approve + follow-ups / fail) is made on this PR (or via the Architect, who records it on the PR).
- **Human PRs**: PR template asks for scope, touched ownership areas, contract changes (must reference an Architect decision), dependency changes (exact versions), how it was tested.
- Small and frequent; rebase on `main` before requesting review.
- After every merge to `main`: smoke-deploy runs; Foreman merges `main` into the current wave branch.

### 5.3 Code ownership (folder level)

`.agentthon/ownership.yml` — source of truth, maintained by the Architect with the team, granular to folders:

```yaml
# example only — real paths come from the project's architecture
areas:
  - path: "backend/extraction/**"
    owner: agents
    reviewers: ["@teammate-a"]
  - path: "frontend/src/views/timeline/**"
    owner: "@teammate-b"
  - path: "contracts/**"
    owner: architect
    change_rule: "only via Architect decision; all owners notified"
  - path: "package.json, requirements*.txt, lockfiles"
    owner: shared
    change_rule: "declare in PR; exact versions; one approval from each affected owner"
  - path: ".agentthon/**"
    owner: architect
```

- Owner types: `agents`, a person, `architect`, `shared`.
- Agents may only write to `agents`-owned paths. graph-checker rejects tasks whose `owns_files` fall outside them; `ownership-check.sh` fails the gate if a diff touches anything else.
- Humans own their folders; agents treat them as read-only and code against their interfaces.
- `shared` and `architect` paths change only through the stated rule.
- CODEOWNERS is generated from ownership.yml so GitHub requests the right reviewers automatically.
- Ownership can be transferred (e.g. a person hands a folder to agents) — Architect updates ownership.yml in a small PR.

### 5.4 TEAM.md — shared practices

Generated at init, adjusted in session 0. Covers:

- **Before touching anything:** check ownership.yml. Yours → go. Not yours → ask the owner (or, for agent areas, ask the Architect to create a task). Contracts/shared → Architect.
- **Claiming work:** humans claim an area or task in `.agentthon/claims.md` (name, path, until when); Foreman skips claimed paths; the Architect won't plan agent tasks there.
- **Interfaces first:** when a human area and an agent area meet, the contract is agreed via the Architect before either side builds.
- **Hot zones:** contracts, shared types, config, dependency files — announce before changing, change in a dedicated small PR.
- **Sync rhythm:** pull `main` at least at every wave merge; Architect gives a short status at each wave release (done, parked, open questions, open PRs).
- **Reviewing agent PRs:** a human owner of affected areas reviews; focus on behaviour and demo fit, since gates already cover mechanics.
- **Conflicts:** if a human change conflicts with an agent wave, the human change wins on human-owned paths; the Foreman re-runs the affected tasks.
- **Demo freeze:** from `hackathon.end − N hours`, only fixes are merged; agent waves still build but PRs wait.

### 5.5 Teammates using other AI coders (GitHub Copilot, Codex, …)

Rules must hold no matter which tool writes the code. Two principles: **one source, many instruction files** and **enforce in CI, not in prompts**.

**One source → generated instruction files.** `scripts/sync-instructions.sh` builds tool-specific files from `TEAM.md`, `conventions.md`, `ownership.yml`, `contracts/` and the context packs:

| File | Read by |
|---|---|
| `AGENTS.md` | Codex and other tools that follow the AGENTS.md convention |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `CLAUDE.md` | Claude Code sessions outside Agent-thon |

Content (kept short so it fits every tool's context): project purpose in two lines, stack, conventions, ownership summary ("you may change: …; ask first: …; never: …"), contract locations, how to run checks, branch/PR rules, exact-version rule. Regenerated by the Architect whenever any source changes (in the same PR); CI fails if the generated files are out of date.

**Enforcement in CI (tool-independent).** The GitHub Actions workflow runs on every PR, regardless of author:
- `gate.sh` (project checks)
- `ownership-check.sh` — touched paths vs ownership.yml and the PR author; changes to `architect`/`shared` paths require the stated approval
- contract check — generated types match `contracts/`
- dependency check — exact versions only
- instruction-files-in-sync check

`.pre-commit-config.yaml` runs the same checks locally for fast feedback in any editor.

**Getting requests to the Architect without Claude.** Teammates who don't use Claude Code open a GitHub issue labelled `architect` (or add to `.agentthon/requests.md`). The Architect reads these at the start of every turn, applies the same brief/challenge rules, and answers on the issue — by changing a contract, updating ownership, or adding tasks to a wave.

**Reviewing AI-written PRs.** All PRs get the same treatment whatever wrote them: CI gates + CODEOWNER review. Agent-thon's reviewers do not review human PRs by default; a teammate can ask for it by adding the label `agent-review` (Foreman runs the combined reviewer on that PR and posts the verdict as a comment).

---

## 6. Gate flow

Per task:
```
implementation (+unit tests) → gate.sh (checks + ownership) → reviewers (per profile)
  → NEEDS_CHANGES → bug-fixer (attempts per profile) → re-gate
  → PASS → merge into agentthon/wave-N → tester-contract
  → exhausted → PARK + questions.md
```

Per wave:
```
merge main into wave → integration → e2e → [eval] → open PR to main
  → human review (+ eval decision) → human merge → deploy from main → smoke-deploy
```

A wave that fails its gates never gets a PR; the deployed `main` stays as it was.

---

## 7. Eval (human-approved)

- Golden set built per project in session 0 / wave planning: input documents + expected structured output (designed with `playbooks/eval-design.md`).
- **Hard failures auto-block** (crash, invalid output format, missing provenance) → bug-fixer.
- **Scores go to the humans**: `evals/eval-wave-N.md` with metrics chosen in the domain brief (e.g. field-level precision/recall, attribute accuracy, provenance coverage) + delta vs previous wave, expected-vs-actual failures, grouped patterns, suggested fix tasks, recommendation.
- The report is attached to the wave PR. Decision: **approve** (PR can merge) / **approve + follow-ups** (merge; fixes into next wave) / **fail** (PR stays open; fix tasks prioritised; eval reruns).
- Building continues on the next wave while a decision is pending. No auto-approve.

---

## 8. Playbook: text → structured data (`playbooks/text-to-structured.md`)

Generic method every extraction/AI builder and the domain reviewer follow. The Architect applies it per project; no libraries are prescribed.

1. **Schema first.** Define the target record (fields, types, required/optional, enumerations, units) in `contracts/` before extracting anything. Every record carries provenance: source document, location (page/offset/span), extraction method, confidence.
2. **Profile the input.** Formats (PDF, scans, DOCX, structured exports, free text), language(s), layout, noise, volume. Choose tools only after profiling — and record the choice and alternatives in `architecture.md`.
3. **Ingest → normalise text.** Format-specific readers, OCR only if needed, preserve page/offset mapping for provenance, sectioning (headers, lists, tables).
4. **Choose the extraction strategy per field**, cheapest reliable first:
   - deterministic: already-structured sources, regex/patterns, dictionaries/lookup tables
   - NLP libraries suited to the language and domain (entity recognition, sentence/section splitting)
   - LLM extraction with a strict output schema
   - hybrid: rules/NLP candidates + LLM for disambiguation, or LLM extraction + rule validation
5. **Context attributes.** Handle negation, uncertainty/hedging, temporality (dates, relative dates, date precision), subject (who the statement is about), and historical vs current.
6. **Normalisation.** Map values to canonical forms / code systems where the domain has them; keep the original text alongside.
7. **Validation.** Schema validation on every record; reject or flag rather than silently fix; dedupe and merge across documents with explicit rules.
8. **LLM rules.** Structured output validated against the schema; every derived claim cites record IDs; user-supplied text treated as untrusted (prompt-injection safe); provider-agnostic adapter configured by env vars; deterministic fake for tests.
9. **Evaluate.** Golden set, field-level metrics, error analysis by category; regressions visible per wave.
10. **Expose uncertainty.** Confidence and provenance reach the UI so users can check the source.

---

## 9. Usage limits and resume

1. Checkpoint to `state.json` after every step.
2. On a usage-limit error, Foreman stops cleanly; `status.md`: `PAUSED: usage limit. Switch account (/logout → /login), set profile, run: foreman resume`.
3. Switch to own Max-subscription account (Anthropic terms don't allow sharing logins — a teammate resumes from their own session instead).
4. `foreman resume` asks once for the profile, then continues unattended from the exact step.
5. Architect/Prototyper: all output is in files; after a switch they re-read and continue.
6. `wait-and-resume.sh` (optional): sleep until reset, then resume.
7. `usage-log.jsonl` per wave — used in the dry run to choose pro vs max.

---

## 10. Token discipline

- Tools before LLM (`gate.sh`).
- Reviewers get diff + relevant context pack + contract excerpt only.
- Task specs self-contained with "Files to Read" + line ranges.
- Structured JSON verdicts from all reviewers/testers.
- On pro, prototype in Claude Code rather than Claude.ai chat (shared usage pool).

---

## 11. Deploy

- Target chosen per project (`config.deploy`); `playbooks/deploy-targets.md` covers common targets (e.g. Railway) — services, env vars, health checks, rollback.
- Deploys happen from `main` only (target watches the GitHub repo, or CI deploys on merge).
- smoke-deploy after each deploy; rollback via the target's previous deployment.
- Runtime secrets live in the deploy target's env vars; never in the repo or agent context.

---

## 12. Permissions (unattended runs)

- Project `.claude/settings.json` allowlist built from `config.checks` + git, gh, package managers, deploy CLI.
- Deny: writes outside project folder, `contracts/**` and `.agentthon/ownership.yml` (except Architect), `.env*`, `git push` to `main`, `gh pr merge`.
- No `--dangerously-skip-permissions`.

---

## 13. Build steps (before the event)

1. Fork Agents-max → `~/ClaudeFolder/Agent-thon`; strip Researcher, Launcher ceremony, unused sub-agents; remove project/stack-specific assumptions.
2. `agentthon-init` skill: project layout, settings, TEAM.md, PR template, CI workflow, ownership.yml, generated AGENTS.md / copilot-instructions.md / CLAUDE.md, pre-commit config, `architect` issue label, branch-protection instructions.
3. Profile config; `run-agent.sh` reads it.
4. Architect prompt: Brief & Challenge, stack/domain decisions → config + domain brief/checklist, ownership.yml + CODEOWNERS, waves, `questions.md`, eval/PR presentation, context packs.
5. Prototyper prompt: brief-driven, demo-script check.
6. Foreman from current Builder: profile-aware, wave/task branches, main sync, PR creation, ownership enforcement, claims, checkpoint/resume, limit handling, lock, `status.md`.
7. New agents: builder-extraction, builder-ai-integration, reviewer-domain (reads project checklist), reviewer-combined, tester-contract, tester-eval.
8. Playbooks: text-to-structured, eval-design, deploy-targets.
9. Scripts: `gate.sh` (config-driven), `ownership-check.sh`, CODEOWNERS generator, `sync-instructions.sh`, `wave-ingest`, `run-eval.sh`, `wait-and-resume.sh`, usage log.
10. Model aliases everywhere; no-`^`/`~` rule in conventions template.
11. Dry run on pro with a toy text → structured → view app, two people working in parallel (one human branch using Copilot or Codex + one agent wave) — verify the instruction files are picked up and CI blocks an out-of-ownership change. If one wave uses more than ~1/3 of a 5-hour window, buy one month of Max.

---

### 13a. Build order (hackathon within a week)

Must-haves first, as a working system; the full plan stays the target. Each phase ends with a user review.

| Phase | Content | Priority |
|---|---|---|
| A | Foundation: toolkit repo, layout, config + profiles, templates, `run-agent.sh`, `agentthon-init` (script + folder-level skill at `~/ClaudeFolder/.claude/skills/`), state/lock helpers | must |
| B | Architect (Brief & Challenge, decisions → config, domain brief/checklist, ownership, waves) + Prototyper | must |
| C | Foreman (profile-aware loop, branches, gates, checkpoint/resume, limit pause, PR creation) + `gate.sh`, `ownership-check.sh`, `wave-ingest` | must |
| D | Workers: builders (api, extraction, ai-integration, ui, composer, infra, bug-fixer, debuggers), reviewer-combined + checklists, tester-contract/integration/e2e/smoke; text-to-structured playbook | must |
| E | Team: TEAM.md, PR template, CI workflow, CODEOWNERS generator, `sync-instructions.sh` (AGENTS.md / copilot / CLAUDE.md), claims | must |
| F | Dry run on a toy project | must |
| G | Separate reviewers (max profile), tester-eval + eval-design playbook + `run-eval.sh`, `agent-review` label, `wait-and-resume.sh`, usage log, deploy-targets playbook, pre-commit, Patcher port | later |

GitHub: toolkit is a local git repo; a private GitHub repo is created after Phase A with user confirmation before the first push.

---

## 14. Decisions log

| Topic | Decision |
|---|---|
| Base | Fork of Agents-max |
| Project specifics | None in toolkit; decided per project by Architect + team, stored in `.agentthon/` |
| Text → structured | Generic playbook; tools chosen per project after profiling the data |
| Profiles | `pro` / `max` switch, read at the start of each wave |
| Overflow | clean pause → switch account → `foreman resume` (asks profile) |
| Purpose & scope | Architect session 0 interviews and challenges; one round per point; output `brief.md` |
| Team workflow | branches per person/wave/task; PR to protected `main`; human merges; merge = deploy |
| Ownership | folder-level `ownership.yml` → CODEOWNERS; agents write only agent-owned paths; claims file; TEAM.md practices |
| Other AI coders | one source → generated AGENTS.md / copilot-instructions.md / CLAUDE.md; rules enforced in CI for every PR; requests via `architect` issues |
| Deploy | per-project target; from `main` only; smoke after deploy |
| Runtime LLMs | app's own concern; provider-agnostic adapter; outside Agent-thon |
| Eval | hard failures auto-block; scores → human decision on the wave PR |
| Project scoping | toolkit global; per-project `.agentthon/`; one Foreman per project |
