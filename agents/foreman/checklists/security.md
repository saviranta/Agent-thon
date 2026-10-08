# Checklist: security

- [ ] **Input handling:** all external input (requests, uploaded files, documents, query params, headers) validated at the boundary; size/type limits enforced server-side.
- [ ] **Files:** no trust in client filenames/content types; no path traversal (user input never joined into paths); uploads stored outside served paths; temp files cleaned up.
- [ ] **Injection:** no string-built SQL/shell/eval/templates with user data; parameterised queries; output encoded for its context (HTML, JSON).
- [ ] **Prompt injection:** user-supplied content passed to LLMs is delimited as data; instructions inside it can't change tools, system prompt, or output contract; LLM output is validated before use and never executed.
- [ ] **Secrets:** none in code, tests, fixtures, logs or error messages; read from env vars; `.env*` not committed.
- [ ] **Sensitive data:** not logged; only the minimum sent to external services, per the domain brief; error responses don't leak internals or stack traces.
- [ ] **Access:** endpoints that expose a person's data enforce whatever access rule the spec defines (e.g. a read-only view can't modify); IDs aren't guessable where that matters.
- [ ] **Dependencies:** no packages with known critical vulnerabilities at the pinned version; no unexpected network calls or telemetry.
- [ ] **CORS / headers:** only the origins configured in the spec; no wildcard with credentials.
