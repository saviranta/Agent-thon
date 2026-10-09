# Checklist: UI

- [ ] Matches the frozen prototype for the screen ids in the spec: layout, hierarchy, copy, spacing, navigation (screenshot vs prototype when available).
- [ ] Kit components as the design system's component map says (right component and variant); no hand-rolled duplicates, no second UI library.
- [ ] Tokens only (colours, type, spacing, radii, shadows, motion) via the theme; one accent colour; one icon set.
- [ ] Every data view has empty (icon + sentence + action), loading (skeleton), error (next step) and populated states, as the UI spec defines.
- [ ] Looks finished: clear primary action, readable type hierarchy, aligned edges, no default browser styles, no raw JSON or unformatted model output.
- [ ] Shows data as the contract provides it; unknown/low-confidence values and provenance displayed as the UI spec says; AI-generated content distinguishable where required.
- [ ] Accessibility basics: semantic elements, labelled inputs, keyboard-reachable actions, visible focus, sufficient contrast (also on a projector), alt text for meaningful images.
- [ ] Works at the demo resolution in `design-system.md` (and mobile if specified).
- [ ] Stable test selectors and routes per conventions / `screens.json`.
- [ ] No sensitive data in URLs, console logs or client-side storage beyond what the spec allows.
