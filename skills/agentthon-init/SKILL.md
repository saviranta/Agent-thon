---
name: agentthon-init
description: Initialise a new or existing project for the Agent-thon multi-agent toolkit (Architect, Prototyper, Foreman). Use when the user says "agentthon-init", "init agent-thon", or wants to set up a project for Agent-thon.
---

# agentthon-init

Set up a project so the Agent-thon agents can work on it. Ask one question at a time and keep it short.

## Steps

1. Ask: **new project or adopt an existing folder?**
2. New: ask for the project name (letters, digits, `.`, `_`, `-`). It will be created at `~/ClaudeFolder/ClaudeProjects/<name>`.
   Adopt: ask for the path. It must be inside `~/ClaudeFolder`.
3. Ask for a one-line description.
4. Ask which profile to start with: **pro** (one worker, combined review per wave) or **max** (3 parallel workers, separate reviewers per task). Default: pro.
5. Confirm the summary with the user, then run:
   ```bash
   bash ~/ClaudeFolder/Agent-thon/scripts/agentthon-init.sh <new|adopt> <name-or-path> "<description>"
   ```
6. If the profile is not `pro`:
   ```bash
   bash ~/ClaudeFolder/Agent-thon/scripts/profile.sh <project-path> set max
   ```
7. Run `bash ~/ClaudeFolder/Agent-thon/scripts/validate.sh <project-path>` and show the result. WARN lines are expected at this point (no GitHub remote, no checks, no brief yet).
8. Tell the user the next steps:
   - Create a GitHub repo and add it as `origin` (needed for PRs). Teammates clone it.
   - Start the Architect for session 0 (Brief & Challenge):
     `bash ~/ClaudeFolder/Agent-thon/scripts/run-agent.sh architect <project-path>`

Do not start agents or dev servers yourself.
