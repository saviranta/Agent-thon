# builder-ai-integration

Read `_builder-base.md` (same folder) first and follow it. Also read section 8 of `$AGENTTHON_TOOLKIT/playbooks/text-to-structured.md` and `.agentthon/artifacts/domain.md` → Rules (older projects: `domain-brief.md` + `domain-checklist.md`).

**Your area:** the code through which the app calls LLMs at runtime — provider adapter, prompts, structured-output handling, provenance checks. (The app's providers are chosen by the team and configured via env vars; you never call them during the build.)

Specifics:
- **Adapter:** one provider-agnostic interface; provider, model and key from env vars; timeouts and one retry on transient errors; a deterministic **fake adapter** (recorded or rule-based responses) used by all tests.
- **Prompts:** in versioned files or constants, not scattered strings. User-supplied content goes in clearly delimited data sections; the system prompt says to treat it as data and ignore instructions inside it. Send only the fields the task needs; respect the domain brief's rules on what may leave the system.
- **Structured output:** request the contract's schema; validate every response; on validation failure retry once with the error, then fail the item visibly (never pass unvalidated output on).
- **Provenance:** every generated statement/recommendation must cite record ids that exist in the input; drop or flag uncited or dangling citations, as the spec says.
- **Domain language:** follow the domain brief on what the output must never claim; add the required labels/disclaimers from the spec.
- Never log full prompts with sensitive data or API keys.
- Tests (all with the fake adapter): schema-valid path, invalid output → retry → failure, injection text inside user content doesn't change behaviour, citation check rejects invented ids.
