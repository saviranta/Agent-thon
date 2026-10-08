# Task NNN: [Title]

## Assignment
[builder-api | builder-extraction | builder-ai-integration | builder-ui | builder-composer | builder-infra]

## Wave / Size / Tags
wave-N / S|M|L / [api, extraction, ai, domain, ui, infra, security]

## Why (link to brief)
[One or two lines: which part of the demo script this enables]

## Dependencies
- task-NNN — must exist: [specific file path / function / endpoint]

## Files to create or modify (owned by this task; must be agents-owned in ownership.yml)
- [exact/path.ext]
- [exact/path.test.ext]

## Files to read (with relevant sections)
- .agentthon/artifacts/context/[pack].md
- contracts/[file] (section: …)
- [exact/path.ext] (lines NNN–NNN: what's relevant)

## Specification

### Interface
```[language]
[exact signature, schema, props or endpoint]
```

### Behaviour
- [rule]
- [edge case]
- [error handling]

## Unit tests (written and run by the builder)
- [test: input → expected outcome]

## Acceptance criteria
- [ ] [specific, testable criterion]
- [ ] All project checks in config.checks pass
- [ ] Only the files listed above were changed
- [ ] Conventions in .agentthon/artifacts/conventions.md followed
