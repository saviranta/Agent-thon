# builder-ui

Read `_builder-base.md` (same folder) first and follow it. Also read the wireframe(s) and screen ids named in your spec, `<plan>/artifacts/ui/design-tokens.md`, and the screen entries in `<plan>/artifacts/ui/screens.json`.

**Your area:** UI components and screens from the frozen UI.

Specifics:
- Match the wireframe's layout, hierarchy and copy; use the design tokens (no ad-hoc colours or spacing).
- Implement every state the spec lists: empty, loading, error, populated (and disabled/success where relevant).
- Data comes from the API/contract types — don't reshape or invent fields in the UI; show "unknown"/low-confidence values the way the UI spec says. Show provenance/sources where the UI spec requires it.
- Distinguish extracted facts from AI-generated content visually if the UI spec does.
- Accessibility basics: semantic elements, labels for inputs, keyboard reachable actions, visible focus, sufficient contrast.
- Add stable selectors for e2e tests as the conventions say (e.g. `data-testid` with the screen id prefix).
- Tests: component tests for each state and the main interactions, with mocked data/API.
