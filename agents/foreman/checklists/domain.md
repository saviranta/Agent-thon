# Checklist: domain (generic part)

Always apply **together with the project's own checklist**: `.agentthon/artifacts/domain.md` → Checklist (written by the Architect; older projects: `domain-brief.md` + `domain-checklist.md`). If that file is missing, review with this generic list and add a `notes` line that the project checklist is missing.

- [ ] Structured output validates against the contract; "unknown" is represented as the contract says — never filled with invented values.
- [ ] Provenance present on every record/statement where the domain brief requires it (source, location/span, method, confidence).
- [ ] Context attributes handled as specified: negation, uncertainty/hedging, temporality (absolute/relative dates, precision), subject (who it's about), historical vs current.
- [ ] Normalisation keeps the original text next to the normalised/coded value.
- [ ] AI-generated statements cite existing record ids; uncited or dangling citations are rejected or flagged, not shown as fact.
- [ ] Output never claims more than the domain brief allows (e.g. decision support vs. decisions); required labels/disclaimers present.
- [ ] Data rules from the domain brief respected: what may be stored, logged, or sent to external services.
- [ ] Test fixtures are synthetic and cover the tricky domain cases the spec lists.
