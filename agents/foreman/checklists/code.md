# Checklist: code

- [ ] Implements the spec's behaviour and every acceptance criterion; edge cases and error handling as specified.
- [ ] Interfaces match `contracts/` exactly (names, types, required/optional, error formats); no silent reshaping.
- [ ] Logic errors: off-by-one, wrong conditions, unhandled null/empty, wrong units/timezones, mutation of shared state, async/await mistakes, race conditions.
- [ ] Errors are handled or propagated deliberately — no swallowed exceptions, no generic catch-all that hides failures.
- [ ] Unit tests actually test the behaviour (would fail if the code were wrong), cover the spec's listed cases, and are deterministic and offline.
- [ ] Conventions from `conventions.md` followed (naming, structure, logging rules).
- [ ] Dependencies: only those named in the spec/context pack, exact versions, no unnecessary heavy additions.
- [ ] No dead code, debug leftovers (`[DEBUG_AGENT]`, stray prints), commented-out blocks, or TODOs that hide missing spec behaviour.
- [ ] Simplicity: no speculative abstraction or features beyond the spec.
