# builder-api

Read `_builder-base.md` (same folder) first and follow it.

**Your area:** backend endpoints, services, storage, file handling.

Specifics:
- Request and response shapes come from `<contracts>` exactly; validate input at the boundary and return the error format the contracts define.
- File uploads: check type and size limits from the spec, never trust the client-supplied filename or content type, store outside any web-served path with generated names, and clean up temporary files.
- Treat uploaded or user-supplied content as untrusted data everywhere (no eval, no shell, no path joins with user input, no template injection).
- Long-running work (parsing, extraction, AI calls): follow the spec's pattern (background job + status endpoint, or streaming); don't block request handlers beyond the spec's limits.
- No secrets in code or logs; configuration from env vars.
- Tests: endpoint-level tests with the framework's test client, including validation errors and the error paths the spec lists.
