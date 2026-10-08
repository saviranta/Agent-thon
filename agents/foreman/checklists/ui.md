# Checklist: UI

- [ ] Matches the frozen wireframe for the screen ids in the spec: layout, hierarchy, copy, navigation.
- [ ] Design tokens used (colours, type, spacing, radii); no ad-hoc values.
- [ ] Every data view has empty, loading, error and populated states, as the UI spec defines.
- [ ] Shows data as the contract provides it; unknown/low-confidence values and provenance displayed as the UI spec says; AI-generated content distinguishable where required.
- [ ] Accessibility basics: semantic elements, labelled inputs, keyboard-reachable actions, visible focus, sufficient contrast, alt text for meaningful images.
- [ ] Works at the widths the UI spec targets (at least desktop; mobile if specified).
- [ ] Stable test selectors present per conventions.
- [ ] No sensitive data in URLs, console logs or client-side storage beyond what the spec allows.
