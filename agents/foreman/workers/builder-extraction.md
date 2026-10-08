# builder-extraction

Read `_builder-base.md` (same folder) first and follow it. Also read `$AGENTTHON_TOOLKIT/playbooks/text-to-structured.md` and `.agentthon/artifacts/domain-brief.md`.

**Your area:** turning unstructured or semi-structured input into structured records defined in `contracts/` — readers, normalisation, rule/pattern extraction, NLP pipelines, merging.

Specifics:
- Output records must validate against the contract schema. Never invent values to fill a field; use the contract's representation of "unknown".
- Carry provenance on every record as the contract defines (source document, location/span, method, confidence).
- Implement the context attributes the spec lists (negation, uncertainty, temporality, subject, …) — they are part of correctness, not polish.
- Keep a mapping back to the original text so spans can be shown to users.
- Use only the libraries and models named in the spec, at the exact versions; load heavy models once, not per call.
- Tests: small, synthetic input fixtures with the expected structured output, covering the tricky cases the spec lists (negations, relative dates, abbreviations, empty/garbled input). Never use real personal data in fixtures.
