# builder-infra

Read `_builder-base.md` (same folder) first and follow it.

**Your area:** scaffolding, build and package configuration, containers, deploy configuration, environment variable templates, test infrastructure (runners, fake adapters' wiring, test configs).

Specifics:
- The project's `config.checks.setup` commands must work in a **fresh worktree**: dependency installs come from committed lockfiles; no global installs; no reliance on files outside the repo.
- Make every check command in `<plan>/config.json` → `checks` runnable after your task if the spec says so (e.g. create the lint/type/test configs they rely on).
- Pin every dependency to an exact version, and commit lockfiles you own.
- Environment: create `.env.example` (if owned) listing every variable with a placeholder and a comment; never real values. Read config from env vars at runtime.
- Containers / deploy config: follow `config.deploy` (target, services, health checks). Each service exposes the health endpoint named in `health_checks`, binds to the port from the environment variable the target provides, and starts without manual steps.
- Keep images and installs lean — every fresh worktree and every deploy pays for them.
