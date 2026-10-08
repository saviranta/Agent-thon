# Agent-thon

A project-agnostic multi-agent coding toolkit for hackathons and short team builds, derived from Agents-max.
You talk to the **Architect** and the **Prototyper**; the **Foreman** builds, reviews, tests and opens PRs without supervision.

Full design: [PLAN.md](PLAN.md). Build status: phases A–E done (foundation, Architect + Prototyper, Foreman + gate, workers, team setup). Next: F (dry run). Eval tester and extras come in phase G.

## Flow

1. **Architect, session 0** — interview + challenge → `brief.md`
2. **Prototyper** — wireframes, `screens.json`, "UI frozen for wave N"
3. **Architect** — stack, contracts, ownership, checks; plans wave N; "release wave N" → plan PR
4. **Merge the plan PR** → wave released
5. **Foreman** — builds, reviews, tests the wave → opens wave PR
6. **Merge the wave PR** → deploy from `main`

## Quick start

```bash
# 1. Initialise a project (or use the /agentthon-init skill from ~/ClaudeFolder)
bash scripts/agentthon-init.sh new my-app "One-line description"

# 2. Check the setup
bash scripts/validate.sh ~/ClaudeFolder/ClaudeProjects/my-app

# 3. Talk to the Architect (session 0: Brief & Challenge), then the Prototyper
bash scripts/run-agent.sh architect  ~/ClaudeFolder/ClaudeProjects/my-app
bash scripts/run-agent.sh prototyper ~/ClaudeFolder/ClaudeProjects/my-app

# 4. Let the Foreman build released waves
bash scripts/run-agent.sh foreman ~/ClaudeFolder/ClaudeProjects/my-app
```

## Profiles

| | pro | max |
|---|---|---|
| Interactive / Foreman models | sonnet / sonnet | opus / opus |
| Parallel workers | 1 | 3 |
| LLM review | combined, per wave | separate, per task |

```bash
bash scripts/profile.sh <project>            # show
bash scripts/profile.sh <project> set max    # this machine only; applies from next wave / on resume
bash scripts/profile.sh <project> default max  # shared default in config.json (commit via PR)
```

## Agents

| Agent | Started by | Role files |
|---|---|---|
| Architect | you (`run-agent.sh architect`) | `agents/architect/` (+ task-decomposer) |
| Prototyper | you (`run-agent.sh prototyper`) | `agents/prototyper/` (+ wireframer, flow-mapper) |
| Foreman | you (`run-agent.sh foreman`) | `agents/foreman/AGENT.md`, `worker-contract.md` |
| Builders | Foreman | `workers/builder-{infra,api,extraction,ai-integration,ui,composer}.md` |
| Fixers | Foreman | `workers/bug-fixer.md`, `debugger-quick.md`, `debugger-deep.md` |
| Reviewers | Foreman | `workers/reviewer-{code,security,domain,ui,combined}.md` + `checklists/` |
| Testers | Foreman | `workers/tester-{integration,e2e}.md` |

## Team setup per project

1. `agentthon-init.sh` creates `TEAM.md`, PR template, CI (`checks`, `ownership`, `hygiene` jobs), CODEOWNERS and the AI-coder instruction files.
2. Create the GitHub repo, add `origin`, push `main`, run `protect-main.sh` (branch protection needs a public repo or GitHub Pro/Team for private repos).
3. Teammates clone it; their AI tools (Copilot, Codex, Claude Code) read the generated instruction files; CI enforces the rules on every PR.

## Requirements

Claude Code, git, Python 3, `gh` (authenticated). Optional: GitHits MCP configured in Claude Code (the Architect uses it for library discovery).

## Billing

`run-agent.sh` ignores `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` from your shell so agents use your Claude subscription login (Pro/Max). Set `AGENTTHON_AUTH=api` to bill an API key deliberately. Check with `/status` inside a session.

## Usage limit reached

The Foreman stops cleanly and says so in `.agentthon/runtime/status.md`. Switch account (`/logout`, `/login`), then:

```bash
bash scripts/run-agent.sh foreman <project> resume
```

## Scripts

| Script | Purpose |
|---|---|
| `agentthon-init.sh` | create/adopt a project |
| `validate.sh` | check project setup |
| `run-agent.sh` | start architect / prototyper / foreman scoped to one project |
| `profile.sh` | show/switch profile, resolve models and settings |
| `state.sh` | runtime state, Foreman lock, checkpoints, pause |
| `check-wave.py` | deterministic wave validation (ownership, claims, overlaps, deps, specs) |
| `allow-domain.sh` | add approved network domains to a project's sandbox |
| `foreman.py` | Foreman mechanics: waves, tasks, worktrees, merges, PRs, status |
| `gate.sh` | config-driven checks + ownership check (used by the Foreman and CI) |
| `ownership-check.py` | ownership rules for task worktrees and PRs |
| `smoke.sh` | health checks after deploy |
| `update-tools.sh` | copy CI scripts into `<project>/.agentthon/bin/` |
| `gen-codeowners.py` | `.github/CODEOWNERS` from `ownership.yml` |
| `sync-instructions.py` | `AGENTS.md`, `.github/copilot-instructions.md`, `CLAUDE.md` from one source |
| `check-versions.py` | reject `^`, `~`, ranges in package.json / requirements |
| `protect-main.sh` | GitHub branch protection + `architect` / `agent-review` labels |

## Project layout

```
<project>/
  .agentthon/            shared, committed: config, ownership, claims, artifacts, waves, evals
  .agentthon/runtime/    local, gitignored: state, lock, status, checkpoints, logs
  .claude/settings.json  project-scoped permissions
  CLAUDE.md              pointer for any Claude Code session
```
