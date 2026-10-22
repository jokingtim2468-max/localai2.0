# Eclipse UI spec

Source of truth for colours, type, spacing and motion. Tokens live in `eclipse/src/theme.css`.

## Colour
| token | value | use |
|---|---|---|
| --bg | #0A0A0A | window background |
| --panel | #121212 | rail, tabs, inspector, drawer, status bar |
| --raised | #1A1A1A | inputs, user bubbles, floating chrome |
| --border | #262626 | every hairline |
| --text / --muted | #E0E0E0 / #8A8A8A | body / secondary |
| --accent / --accent-hover | #FF6D00 / #FF8C00 | buttons, active tab, focus ring, caret, selection ONLY |
| --ok / --danger | #3DDC84 / #FF3B30 | results, errors |

No gradients, no purple, no glow.

## Type
JetBrains Mono for code, terminal, numbers, timers. Inter Tight for UI text (SF Pro fallback).
Both bundled offline (@fontsource). Labels are sentence case; no tracked-out all-caps.

## Depth (anti-vibe rules)
- Elevation by layer: e1 panels, e2 floating chrome (composer, approval), e3 modals (palette).
- Radius by hierarchy: 4px tabs/rail, 6px controls, 10px floating surfaces.
- Frosted glass only on floating chrome (command palette), with a solid fallback. Never under body text.
- Faint grain over the background (3.5% opacity) so large flat areas are not sterile.
- Buttons sink to 97% on press.
- Banned: purple, gradient washes, identical cards, 01/02/03 markers, arrow-on-every-button, middle-dot meta strings, generic empty-state copy.

## Layout
Left icon rail (48px) | tabbed centre | right inspector (280px) | bottom drawer (terminal + logs, 180px) | status bar (24px).
Every panel can be hidden; Ctrl/Cmd+K opens the command palette.

## Motion
150 ms ease-out. Panels open from the button that opened them. Thinking indicator = a moon
crossing a sun (Web Animations API, so it runs even with OS animations off; Reduce motion slows it).
