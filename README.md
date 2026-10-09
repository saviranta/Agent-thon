# Agent-thon

A project-agnostic multi-agent coding toolkit for hackathons and short team builds, derived from Agents-max.
You talk to the **Architect** and the **Prototyper**; the **Foreman** builds, reviews, tests and opens PRs without supervision.

Full design: [PLAN.md](PLAN.md). Playbooks: `playbooks/` (library discovery, visual quality, text → structured). Build status: phases A–E done, F (dry run) in progress, agent home + split phase added. Eval tester and extras come in phase G.

## Two folders per project

```
ClaudeProjects/
  my-app/          product repo — product code only, in the layout folders (e.g. frontend/ api/ analytics/)
  my-app-agents/   agent home — its own (private) repo: brief, chunks, contracts source, ownership,
                   claims, waves, specs, artifacts, TEAM.md; runtime/ stays local
```

Nothing from Agent-thon is ever committed to the product repo. The only thing the agents put there is product code (wave PRs) and the published contracts (contracts PRs).

## Flow

1. **Architect, phase 0** — interview + challenge → `artifacts/brief.md`
2. **Architect, phase 1: Split & Contracts** — product layout, chunks with owners (people or `agents`), contracts + examples, contract review, freeze → **contracts PR** in the product repo. Merge it: everyone starts building their chunk independently.
3. **Prototyper** (in parallel from phase 0, the team's designer) — use cases, visual direction, **design system** (UI kit chosen with GitHits + tokens, frozen with the contracts), hi-fi prototypes, "UI frozen for wave N"
4. **Architect, phase 2** — libraries, conventions, checks, domain rules, context packs for the agent chunks
5. **Architect, phase 3** — plans wave N for the agent chunks; "release wave N" → **plan PR in the agent home repo**
6. **Merge the plan PR** → wave released
7. **Foreman** — builds, polishes the UI (screenshots vs prototypes), reviews, tests the wave in product-repo worktrees → **wave PR in the product repo**
8. **Merge the wave PR** → deploy from `main`

## Quick start

```bash
# 0. Once per machine: the toolkit's own Python env (contract example validation)
bash scripts/setup-toolkit.sh

# 1. Set up a project (or use the /agentthon-init skill from ~/ClaudeFolder)
bash scripts/agentthon-init.sh new   my-app "One-line description"          # new product repo + agent home
bash scripts/agentthon-init.sh adopt ~/ClaudeFolder/ClaudeProjects/my-app "…"  # existing repo: only adds my-app-agents/

# 2. Check, then share the agent home (private GitHub repo + labels)
bash scripts/validate.sh     ~/ClaudeFolder/ClaudeProjects/my-app
bash scripts/github-setup.sh ~/ClaudeFolder/ClaudeProjects/my-app

# 3. Talk to the Architect, then the Prototyper (either folder works as <project>)
bash scripts/run-agent.sh architect  ~/ClaudeFolder/ClaudeProjects/my-app
bash scripts/run-agent.sh prototyper ~/ClaudeFolder/ClaudeProjects/my-app

# 4. Let the Foreman build released waves (one machine at a time)
bash scripts/run-agent.sh foreman ~/ClaudeFolder/ClaudeProjects/my-app
```

Tip: `export PATH="$HOME/ClaudeFolder/Agent-thon/scripts:$PATH"` in `~/.zshrc` lets you drop the `bash scripts/` prefix.

## Teammates

Clone both repos side by side (folder names as printed by `github-setup.sh`). Each person builds their chunk against the published contracts in the product repo, claims areas in `claims.md`, and talks to the Architect directly, via `requests.md`, or with an issue labelled `architect` in the agent home repo. Rules: `TEAM.md` in the agent home.

## Profiles

| | pro | max |
|---|---|---|
| Interactive / Foreman models | sonnet / sonnet | opus / opus |
| Parallel workers | 1 | 3 |
| LLM review | combined, per wave | separate, per task |

```bash
bash scripts/profile.sh <project>              # show
bash scripts/profile.sh <project> set max      # this machine only; applies from next wave / on resume
bash scripts/profile.sh <project> default max  # shared default in config.json (commit in the agent home)
```

## Agents

| Agent | Started by | Role files |
|---|---|---|
| Architect | you (`run-agent.sh architect`) | `agents/architect/` (+ task-decomposer) |
| Prototyper | you (`run-agent.sh prototyper`) | `agents/prototyper/` (+ wireframer for prototypes, flow-mapper) |
| Foreman | you (`run-agent.sh foreman`) | `agents/foreman/AGENT.md`, `worker-contract.md` |
| Builders | Foreman | `workers/builder-{infra,api,extraction,ai-integration,ui,composer}.md` |
| UI polish | Foreman (once per wave with UI) | `workers/ui-polish.md` |
| Fixers | Foreman | `workers/bug-fixer.md`, `debugger-quick.md`, `debugger-deep.md` |
| Reviewers | Foreman | `workers/reviewer-{code,security,domain,ui,combined}.md` + `checklists/` |
| Testers | Foreman | `workers/tester-{integration,e2e}.md` |

Sessions run with the agent home as working directory and the product repo added with `--add-dir`, so Claude Code never writes its own files into the product repo. Settings are generated per machine into `runtime/claude-settings.json`.

## Requirements

Claude Code, git, Python 3, `gh` (authenticated). Optional: GitHits MCP configured in Claude Code (the Architect uses it for library discovery).

## Billing

`run-agent.sh` ignores `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` from your shell so agents use your Claude subscription login (Pro/Max). Set `AGENTTHON_AUTH=api` to bill an API key deliberately. Check with `/status` inside a session.

## Usage limit reached

The Foreman stops cleanly and says so in `<agent home>/runtime/status.md`. Switch account (`/logout`, `/login`), then:

```bash
bash scripts/run-agent.sh foreman <project> resume
```

## Scripts

| Script | Purpose |
|---|---|
| `setup-toolkit.sh` | once per machine: toolkit venv (jsonschema, PyYAML) |
| `agentthon-init.sh` | create/adopt a project (agent home next to the product repo) |
| `github-setup.sh` | private GitHub repo for the agent home + `architect` / `foreman-question` labels |
| `validate.sh` | check project setup |
| `run-agent.sh` | start architect / prototyper / foreman scoped to one project |
| `profile.sh` | show/switch profile, resolve models and settings |
| `state.sh` | runtime state, Foreman lock (local + agent home repo), checkpoints, pause |
| `chunks.py` | check the architecture split; generate `ownership.yml` from `chunks.json` |
| `contracts.py` | check contracts + examples, compare with the product repo, publish (contracts PR), sync into waves |
| `check-wave.py` | deterministic wave validation (layout, ownership, claims, overlaps, deps, specs, contracts) |
| `allow-domain.sh` | add approved network domains (`config.network.allowed_domains`) |
| `foreman.py` | Foreman mechanics: plan refresh, waves, tasks, worktrees, merges, PRs, questions, status |
| `gate.sh` | config-driven checks + exact versions + design tokens + ownership/layout check |
| `check-design.py` | flag raw colours / palette classes in agent-built UI outside the theme files |
| `screenshots.sh` | render app screens + prototypes to PNGs (`config.design.screenshots`) for polish and UI review |
| `ownership-check.py` | ownership, claims, layout and contracts rules for a worktree |
| `check-versions.py` | reject `^`, `~`, ranges in package.json / requirements |
| `smoke.sh` | health checks after deploy |

## Agent home layout

```
<repo>-agents/
  config.json        project, profiles, git (both repos), layout, contracts_dir, team, checks, deploy, network
  chunks.json        the split: chunks, owners, paths, provides/consumes      → ownership.yml (generated)
  claims.md  requests.md  TEAM.md
  contracts/         source of truth (+ examples/<name>/) → published to <repo>/<contracts_dir>/
  artifacts/         brief, architecture, conventions, domain, kickoff, context/,
                     ui/ (use cases, design system + tokens.css, prototypes, screens.json, hero data)
  waves/wave-N/      wave.json + task-specs/ (released by merging a plan PR)
  evals/decisions.md
  runtime/           local only: state, lock, status, plan/ (released plan), worktrees/, results/, settings
```
