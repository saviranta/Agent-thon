# Design system

Status: draft | frozen (YYYY-MM-DD)  ·  Version: 1
Owner: Prototyper (agent home `artifacts/ui/`). Changes after the freeze: additive only, version +1, note it in "Changes".

## Direction
- Chosen option: FILL_IN (from `prototypes/direction-options.html`) — one line on the feel (e.g. "calm, data-dense, light, one teal accent")
- References: FILL_IN (apps/sites the team pointed at)
- Demo resolution: 1440×900 · mobile: yes/no

## Libraries
(record with the format in `$AGENTTHON_TOOLKIT/playbooks/library-discovery.md`; exact versions)
### Component kit
### Icons
### Charts (if any)
### Motion (if any)
### Fonts

## Tokens
Source of truth: `artifacts/ui/tokens.css` (CSS variables). Product theme files map these onto the kit:
- Theme files in the product repo: FILL_IN (also in `config.design.theme_paths`)
- Mapping: FILL_IN (e.g. "Tailwind v4 `@theme inline { --color-primary: var(--ds-color-accent) }`; shadcn `--primary: var(--ds-color-accent)`")

## Component map
Prototype pattern → kit component. Builders use exactly these.
| Pattern | Kit component | Notes (variant, size) |
|---|---|---|
| Primary action | FILL_IN | |
| Card / panel | | |
| Table / list | | |
| Form field | | |
| Dialog / sheet | | |
| Toast / inline error | | |
| Loading | Skeleton | spinners only inside buttons |
| Empty state | | icon + one sentence + action |

## Hero data
Where the demo dataset lives (contract examples or `artifacts/ui/hero-data/`) and what it shows.

## Rules
- Components from the kit only; no raw colours/spacing in components (gate `design` check).
- One accent colour; semantic colours only for status.

## Changes
