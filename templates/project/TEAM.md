# How we work

Short rules so humans, their AI coding tools (Claude Code, Copilot, Codex, …) and the Agent-thon agents can build in the same repo without stepping on each other. The Architect adjusts this file in session 0; change it via the Architect.

## Roles
- **Architect** (agent, run by anyone on the team): purpose, scope, contracts, ownership, task waves. Talk to it directly, or open a GitHub issue labelled `architect`, or add to `.agentthon/requests.md`.
- **Prototyper** (agent): UI design and wireframes.
- **Foreman** (agent, runs on one machine): builds released waves autonomously and opens wave PRs.
- **Humans**: own their areas, review PRs in their areas, decide on scope, merge.

## Before touching anything
1. Look up the path in `.agentthon/ownership.yml` (the summary is in `AGENTS.md`).
   - **Yours** → go ahead.
   - **Someone else's** → ask them first.
   - **agents** → ask the Architect to create a task, or agree with the Architect that you take it over (ownership changes in a small PR).
   - **architect / shared** (contracts, config, dependencies, CI, generated files) → via the Architect, in a small dedicated PR.
2. Check `.agentthon/claims.md`. Claim the area you're about to work on (name, path, until when) and remove the claim when done. Agents never plan work inside a claimed path.

## Branches and PRs
- `main` is protected and always deployable. **Merge = deploy.**
- Your branches: `<name>/<topic>`. Agent branches: `agentthon/*` (Foreman), `plan/*` (Architect), `patch/*` (Patcher).
- Small, frequent PRs. Rebase on `main` before asking for review.
- CI must be green: project checks, ownership check, exact versions, generated files up to date.
- Review: the owners of the touched areas (GitHub requests them via CODEOWNERS).
- **Plan PRs** (`plan/wave-N`): merging one releases that wave to the Foreman.
- **Wave PRs** (`agentthon/wave-N`): review behaviour and demo fit — the gates already covered lint, types, tests and reviews. If the PR says an eval decision is required, decide via the Architect first.

## Interfaces first
Where a human area meets an agent area, agree the contract with the Architect before either side builds. Code against `contracts/`; never change them in a feature PR.

## Hot zones
Contracts, shared types, `.agentthon/config.json`, dependency manifests and lockfiles, CI, generated files (`AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `.github/CODEOWNERS`): announce before changing, one small PR each.

## Dependencies
Exact versions only (no `^`, `~` or ranges). Say in the PR why a new dependency is needed.

## Sync rhythm
- Pull `main` whenever a wave PR is merged.
- The Architect gives a short status at each wave release: done, parked, open questions, open PRs.

## Conflicts
On human-owned paths the human change wins; the Foreman re-runs affected agent tasks. Anything else → the Architect decides with the owners.

## Demo freeze
From `hackathon.end − demo_freeze_hours_before_end` (see `.agentthon/config.json`): only fixes are merged. Agent waves keep building, but their PRs wait.

## Data and secrets
No real personal data in fixtures, screenshots or wireframes. No secrets in the repo; `.env.example` lists variable names only.
