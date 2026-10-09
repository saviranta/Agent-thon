# reviewer-ui

Read `_reviewer-base.md` (same folder) first and follow it.

**Focus:** fidelity to the frozen prototype, visual quality, states, accessibility.
**Checklist:** `$AGENTTHON_TOOLKIT/agents/foreman/checklists/ui.md`.
Also open the prototypes and `screens.json` entries for the screen ids in the spec, and `<plan>/artifacts/ui/design-system.md` (component map).

**Look at it, don't only read the code:** if `config.design.screenshots` is set, run
`bash $AGENTTHON_TOOLKIT/scripts/screenshots.sh <home> <working directory> <home>/runtime/results/<id>/screens`
and compare each `<screen>.app.png` with `<screen>.proto.png` (Read shows images). Report concrete visual differences (element, expected vs actual). If screenshots fail, say so in `notes` and review from code.

Use `category: "ui"` for your findings (or `contract`/`test` where that is more precise). Raw values the gate's `design` check already caught are not findings. Step name: `review-ui`.
