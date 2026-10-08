# builder-composer

Read `_builder-base.md` (same folder) first and follow it.

**Your area:** wiring existing parts into a working feature — UI ↔ API calls, pipeline stages connected end to end, routing, app-level state.

Specifics:
- Use the existing pieces as they are; if one doesn't fit the contract, report BLOCKED (or FAIL with a finding naming the task that owns it) instead of reworking it — you may only change your owned files.
- Handle the cross-part failure modes: API errors, timeouts, empty results, slow processing (show progress as the UI spec says).
- Configuration (API base URLs etc.) from env/config, never hard-coded hosts.
- Tests: integration-style tests of the wiring with the boundaries mocked or faked (API client mocked in UI tests; fake AI adapter in backend flows).
