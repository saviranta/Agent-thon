# Project context

This project is built with Agent-thon. Before changing anything, read:

- `TEAM.md` — how the team works (branches, PRs, claims, when to touch what)
- `.agentthon/ownership.yml` — who owns which folder. Only change paths you own.
- `.agentthon/artifacts/brief.md` — purpose, scope and demo script (once written)
- `.agentthon/artifacts/conventions.md` — coding conventions (once written)

Rules:
- Never commit to `main` directly; work on a branch and open a PR.
- Never read or write `.env*` or `secrets/`.
- Dependency versions are exact — no `^` or `~`.
- Contract changes (`contracts/`) go through the Architect.
