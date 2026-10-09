---
name: agentthon-init
description: Initialise a new or existing project for the Agent-thon multi-agent toolkit (Architect, Prototyper, Foreman). Use when the user says "agentthon-init", "init agent-thon", or wants to set up a project for Agent-thon.
---

# agentthon-init

Set up a project so the Agent-thon agents can work on it. Agent-thon keeps everything it needs in an **agent home** folder next to the product repo (`<repo>-agents/`); the product repo itself gets no Agent-thon files. Ask one question at a time and keep it short.

## Steps

1. Ask: **new project or an existing repo?**
2. New: ask for the project name (letters, digits, `.`, `_`, `-`). The product repo is created at `~/ClaudeFolder/ClaudeProjects/<name>`, the agent home at `~/ClaudeFolder/ClaudeProjects/<name>-agents`.
   Existing: ask for the repo path. It must be a git repo inside `~/ClaudeFolder`; it won't be changed.
3. Ask for a one-line description.
4. Ask which profile to start with: **pro** (one worker, combined review per wave) or **max** (3 parallel workers, separate reviewers per task). Default: pro.
5. Confirm the summary with the user, then run:
   ```bash
   bash ~/ClaudeFolder/Agent-thon/scripts/agentthon-init.sh <new|adopt> <name-or-path> "<description>"
   ```
6. If the profile is not `pro`:
   ```bash
   bash ~/ClaudeFolder/Agent-thon/scripts/profile.sh <agent-home> set max
   ```
7. If `~/ClaudeFolder/Agent-thon/.venv` doesn't exist, run `bash ~/ClaudeFolder/Agent-thon/scripts/setup-toolkit.sh` (once per machine).
8. Run `bash ~/ClaudeFolder/Agent-thon/scripts/validate.sh <agent-home>` and show the result. WARN lines are expected at this point (no remotes, no brief, no chunks, no checks yet).
9. Ask whether to share the agent home on GitHub now (private repo `<owner>/<name>-agents`). Only with a yes:
   ```bash
   bash ~/ClaudeFolder/Agent-thon/scripts/github-setup.sh <agent-home>
   ```
   The product repo needs its own GitHub remote (`origin`) for PRs; tell the user if it has none.
10. Tell the user the next step — start the Architect (phase 0: Brief & Challenge, then phase 1: Split & Contracts):
    `bash ~/ClaudeFolder/Agent-thon/scripts/run-agent.sh architect <agent-home>`

Do not start agents or dev servers yourself.
