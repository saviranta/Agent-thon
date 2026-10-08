# Task NNN: [Title]
<!-- Cap: ~60 lines / 3,500 chars. Point to contracts, context packs and code by path + section; never copy them in. -->

**Builder:** builder-[api|extraction|ai-integration|ui|composer|infra] · **Wave/size:** wave-N / S|M · **Tags:** [api, extraction, ai, domain, ui, infra, security]
**Why:** [one line: which demo-script step this enables]
**Depends on:** task-NNN ([the file / function / endpoint it provides]) | none

## Files (owned; agents-owned in ownership.yml)
- [exact/path.ext]
- [exact/path.test.ext]

## Read
- contracts/[file] → [section / type name]
- .agentthon/artifacts/context/[pack].md → [section]
- [exact/path.ext] → [lines or symbol]

## Do
- Interface: [one line, e.g. `extract(text: str) -> Extraction` per contracts/extraction.schema.json]
- [behaviour rule / edge case / error handling — only what is NOT already in the contract or context pack]

## Unit tests (written and run by the builder)
- [input → expected outcome]

## Acceptance criteria
- [ ] [specific, testable criterion]
- [ ] config.checks pass; only the files above changed; conventions.md followed
