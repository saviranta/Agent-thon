# Playbook: a demo that looks great

Used by the Prototyper (design system, prototypes), builder-ui, ui-polish and reviewer-ui. Judges remember how the demo **looked and felt** in the first 20 seconds. Generic "developer UI" loses to a focused, polished one even when the tech underneath is weaker.

## Decide early, once
- **One component library**, used everywhere. No mixing kits, no hand-rolled buttons next to library buttons.
- **One visual direction** chosen by the team from 2–3 options: palette (neutral base + **one** strong accent + semantic colours), typeface (one family, two at most), density (airy / balanced / dense), corner radius, shadow style, light or dark.
- **Tokens as CSS variables** (`artifacts/ui/tokens.css`) — the single source for colours, type scale, spacing, radii, shadows, motion. Prototypes and the product use the same file.

## What makes it look finished
- **Hierarchy:** one clear primary action per screen; a type scale with real contrast between title, body and meta text.
- **Spacing:** only token steps (e.g. 4/8/12/16/24/32/48); generous whitespace; aligned edges.
- **Real-looking data:** a curated **hero dataset** for the demo — believable names, numbers, lengths of text; never "Lorem ipsum" or "Test 1". Show enough items that lists and charts look alive.
- **States designed, not defaulted:** skeleton loaders instead of spinners on data views; empty states with a short sentence, an icon or illustration and the next action; error states that say what to do.
- **Motion with purpose:** short transitions (150–250 ms) on appearing content, hover/press feedback, progress for long work. Nothing that delays the demo.
- **Icons:** one icon set, consistent stroke and size.
- **Data visualisation:** one chart library styled with the tokens; label axes, no default rainbow palettes.
- **First screen = wow moment:** the screen the demo opens on gets the most care.
- **Responsive enough:** perfect at the demo resolution (usually 1280–1440 wide, projector-friendly contrast); acceptable at 375 if the brief mentions mobile.

## Candidates to check (not defaults — verify with `playbooks/library-discovery.md`)
| Need | Candidates |
|---|---|
| React kit | shadcn/ui (Radix + Tailwind, copy-in components), Mantine, Chakra UI, HeroUI, MUI |
| Vue / Svelte kit | Nuxt UI, PrimeVue · shadcn-svelte, Skeleton |
| Dashboards | Tremor, shadcn charts (Recharts), Apache ECharts |
| Flair (sparingly) | Magic UI, Aceternity UI, Motion (framer-motion), Lottie |
| Icons | Lucide, Phosphor, Tabler |
| Fonts | Inter, Geist, IBM Plex, a display face for the title only |
| Python-only apps | Streamlit (+ theme config), Gradio, NiceGUI, Reflex — limited styling; set the theme and stop |

Prefer kits that are **token-driven** (CSS variables / theme object) so `tokens.css` maps onto them directly.

## Avoid
- Default browser styles, default blue links, unstyled tables.
- More than one accent colour; gradients everywhere; emoji as icons.
- Raw colour/spacing values in components (the gate's `design` check flags colour literals outside the theme files).
- Walls of JSON or raw model output in the UI — format it.
