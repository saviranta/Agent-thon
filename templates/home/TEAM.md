# How we work

Short rules so humans, their AI coding tools and the Agent-thon agents can build in parallel without stepping on each other. The Architect adjusts this file in session 0.

## Two repositories
- **Product repo** (`config.git.github_repo`): product code only, in the layout folders (`config.layout.folders`). Nothing from Agent-thon is ever committed there.
- **Agent home** (`config.git.agents_github_repo`, private): brief, architecture, chunks, contracts source, ownership, claims, waves and task specs, eval decisions. Clone it next to the product repo as `<repo>-agents/`.

## Roles
- **Architect** (agent, run by anyone on the team): purpose, scope, chunks and owners, contracts, task waves for the agent-owned chunks. Talk to it directly, or open an issue labelled `architect` in the agent home repo, or add to `requests.md`.
- **Prototyper** (agent): UI design and wireframes.
- **Foreman** (agent, **one machine at a time**): builds released waves and opens wave PRs in the product repo.
- **Humans**: own their chunks, review PRs in their areas, decide on scope, merge.

## Chunks and ownership
`chunks.json` splits the product into chunks; each has one owner (`agents` or a person) and folders it lives in. `ownership.yml` is generated from it.
- **Your chunk** → go ahead.
- **Someone else's** → ask them first.
- **agents** → ask the Architect for a task, or agree a hand-over (the Architect changes `chunks.json`).
- **Contracts** → only via the Architect (see below).

Claim what you're about to work on in `claims.md` (who, path, until) and remove it when done. Agents never plan work inside a claimed path.

## Contracts
The schemas and API definitions between chunks. Source: `contracts/` in the agent home; published to `config.contracts_dir` in the product repo by a **contracts PR** (`contracts/*` branch).
- Build against the published contracts and their examples; use fakes or fixtures for chunks that don't exist yet.
- Never change the product copy in a feature PR. Need a change → tell the Architect; after the freeze, every chunk owner that provides or consumes the contract agrees first.

## Branches and PRs (product repo)
- `main` is always deployable. **Merge = deploy.**
- Your branches: `<name>/<topic>`. Agent branches: `agentthon/*` (Foreman), `contracts/*` (Architect).
- Small, frequent PRs; rebase on `main` before review. Reviewers: the owners of the touched chunks.
- **Wave PRs**: review behaviour and demo fit — the gates already covered lint, types, tests and reviews. If the PR says an eval decision is required, decide via the Architect first.

## Agent home
- Plan PRs (`plan/wave-N`) in the agent home repo: merging one releases that wave to the Foreman.
- Small direct commits to its `main` are fine for `claims.md` and `requests.md`.

## Dependencies
Exact versions only (no `^`, `~` or ranges). Say in the PR why a new dependency is needed.

## Sync rhythm
- Pull the product repo's `main` whenever a wave or contracts PR is merged; pull the agent home before talking to the Architect.
- The Architect gives a short status at each wave release: done, parked, open questions, open PRs.

## Demo freeze
From `hackathon.end − demo_freeze_hours_before_end` (see `config.json`): only fixes are merged. Agent waves keep building, but their PRs wait.

## Data and secrets
No real personal data in fixtures, screenshots or wireframes. No secrets in either repo; the product repo's `.env.example` lists variable names only.
