# Agent-thon

A project-agnostic multi-agent coding toolkit for hackathons and short team builds, derived from Agents-max.
You talk to the **Architect** and the **Prototyper**; the **Foreman** builds, reviews, tests and opens PRs without supervision.

Full design: [PLAN.md](PLAN.md). Build status: phase A (foundation) done; phases B–F in progress.

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

## Project layout

```
<project>/
  .agentthon/            shared, committed: config, ownership, claims, artifacts, waves, evals
  .agentthon/runtime/    local, gitignored: state, lock, status, checkpoints, logs
  .claude/settings.json  project-scoped permissions
  CLAUDE.md              pointer for any Claude Code session
```
