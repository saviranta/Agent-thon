# builder-ui

Read `_builder-base.md` (same folder) first and follow it. Also read:
- the prototype(s) and screen ids named in your spec (`<plan>/artifacts/ui/prototypes/screen-<id>.html`) and their entries in `<plan>/artifacts/ui/screens.json`
- `<plan>/artifacts/ui/design-system.md` (libraries, token mapping, **component map**) — older projects: `design-tokens.md`
- `$AGENTTHON_TOOLKIT/playbooks/visual-quality.md` → "What makes it look finished"

**Your area:** UI components and screens from the frozen UI, built with the project's component kit.

Specifics:
- **Reproduce the prototype 1:1:** layout, hierarchy, copy, spacing, the hero data's look. Each `data-component` in the prototype maps to the kit component named in the component map — use exactly that component and variant. No hand-rolled replacements for kit components; no second UI library.
- **Tokens only:** colours, type, spacing, radii, shadows, motion from the theme (`config.design.theme_paths`), which maps the `--ds-*` variables from `tokens.css`. No raw colour values or palette classes in components — the gate's `design` check fails on them. If something truly has no token, use the closest one and say so in `notes`.
- **Design-system setup task** (spec says so): install the kit, icons, fonts at the exact versions in `design-system.md`; copy `<plan>/artifacts/ui/tokens.css` unchanged into the theme; map the kit's variables onto the `--ds-*` variables; app shell (layout, navigation, page container); the screenshot script per `conventions.md` (`config.design.screenshots`).
- Implement every state the spec lists: empty (icon + sentence + action), loading (skeletons on data views), error (what to do next), populated — plus disabled/success where relevant. Motion as the design system says.
- Data comes from the API/contract types — don't reshape or invent fields; show "unknown"/low-confidence values and provenance as the UI spec says. Distinguish AI-generated content visually if the UI spec does.
- Accessibility basics: semantic elements, labelled inputs, keyboard-reachable actions, visible focus, sufficient contrast.
- Stable selectors for e2e tests as the conventions say (e.g. `data-testid` with the screen id prefix); the screen's route as in `screens.json`.
- Tests: component tests for each state and the main interactions, with mocked data/API.
- If `config.design.screenshots` is set and the screen renders: `bash $AGENTTHON_TOOLKIT/scripts/screenshots.sh <home> <working directory> <home>/runtime/results/<task-id>/screens`, look at your screen next to its prototype, and fix obvious differences before finishing.
