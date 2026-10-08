# Capture: the design system as it exists

Extracted from `ui/app.css`, 232 lines, on 8 October 2026. Contrast ratios are
computed, not estimated: sRGB relative luminance per WCAG 2.2, in
`_tools/contrast.py`.

## 1. The headline

There are **11 colour tokens and 40 colours**.

Counting rule, because the number changes with it: a hex literal inside the
`:root` block is a token *declaration*, not a literal use. The tool separates
the two and this table follows it.

| | Count |
|---|---|
| Custom properties declared on `:root` | 12 (11 colours, 1 layout) |
| `var()` references | 129 |
| Hex colours in the whole file | 40 distinct, 49 occurrences |
| Of those, the token declarations in `:root` | 11 occurrences |
| Hex colours in rule bodies | 31 distinct, 38 occurrences |
| Rule-body literals that restate a declared token | 2 |
| Genuinely untokenised colours | 29 |
| `rgba()` literals, none tokenised | 9 distinct |
| Distinct `border-radius` values | 12 |
| Distinct `font-size` values | 7, plus the 14 px base |

So the token layer is real and heavily used, and 29 colours sit outside it.

Two rule-body literals restate a token they could have referenced, which is a
defect with no design intent behind it: `#1a1c22` is `--bg2` and `#2b3040` is
`--chip`.

**Correction.** An earlier draft of this document said 51 occurrences, 40
rule-body literals and 11 restated tokens. All three were wrong: the figures
came from a whole-file regex whose grouped output I summed by eye, and it
counted the eleven `:root` declarations as if they were literal uses. The
numbers above come from `_tools/contrast.py`, which is committed and
rerunnable, and that tool is the instrument of record from here on.

## 2. Declared tokens, as they are

| Token | Value | Role in the code |
|---|---|---|
| `--bg` | `#121317` | page background |
| `--bg2` | `#1a1c22` | panel background: header, sidebar, cards, detail, modal, tiles |
| `--bg3` | `#23262e` | raised background: button faces, cover placeholders, bars, meter tracks |
| `--line` | `#2e323c` | every border and divider, decorative and structural alike |
| `--fg` | `#e6e7ea` | body text |
| `--muted` | `#8b90a0` | secondary text, counts, labels, headings |
| `--accent` | `#4f8cff` | links, focus intent, primary fills, active states, progress fills |
| `--ok` | `#3ccf7a` | success text, selected badge, capacity under 80 per cent |
| `--warn` | `#f0b23d` | warning text and pills, capacity 80 to 90 per cent, loose twin matches |
| `--bad` | `#f2575d` | error text and pills, capacity at or above 90 per cent, danger buttons |
| `--chip` | `#2b3040` | chip and pill background |
| `--tile` | `150px` | grid tile width, written at runtime by the tile slider |

## 3. The 29 untokenised colours, grouped by the job they do

These are the tokens the design system is missing. Names proposed; values are
exactly what the CSS uses today.

### State surfaces

| Value | Used for | Proposed token |
|---|---|---|
| `#2a3a5c` | selected and active surface: `button.active`, `.fact.on`, `.lrow.current`, `#toast` | `--surface-selected` |
| `#3a4260` | chip hover | `--surface-chip-hover` |
| `#3a2226` | `button.danger` face | `--surface-danger` |

### Status pills, three pairs

| Background | Foreground | Proposed tokens |
|---|---|---|
| `#1f4d33` | `#8ef0b4` | `--pill-ok-bg`, `--pill-ok-fg` |
| `#4d3d1f` | `#ffd98a` | `--pill-warn-bg`, `--pill-warn-fg` |
| `#4d1f24` | `#ff9aa0` | `--pill-bad-bg`, `--pill-bad-fg` |

### Chip kinds, seven surfaces

| Value | Kind | Proposed token |
|---|---|---|
| `#2f4a3a` | system | `--chip-system` |
| `#4a2f4a` | franchise | `--chip-franchise` |
| `#4a3f2f` | suggested, with a dashed warn outline | `--chip-suggested` |
| `#3d2f4a` | collection | `--chip-collection` |
| `#2f3a4a` | theme | `--chip-theme` |
| `#2f4a48` | mode and perspective, shared | `--chip-mode` |

### The device lamp, six values

| Value | State | Proposed token |
|---|---|---|
| `#3a3f47` | off, fill | `--lamp-off` |
| `#4a505a` | off, inset ring | `--lamp-off-ring` |
| `#33d17a` | on, fill | `--lamp-on` |
| `#2aa35f` | on, ring | `--lamp-on-ring` |
| `#e05252` | trouble, fill | `--lamp-bad` |
| `#b83c3c` | trouble, ring | `--lamp-bad-ring` |

The lamp deliberately never goes red for a device that is merely unplugged. The
comment says so: a handheld on the desk is not an error, and red stays
available for a device in actual trouble. That is a design rule and the rebuild
keeps it.

### Device card text, four near-duplicates of `--muted` and `--fg`

| Value | Used for | Note |
|---|---|---|
| `#9aa3ad` | `.dev-state`, `.card.offline h3` | 7 per cent lighter than `--muted` |
| `#8b939d` | `.dev-figs span` | 1 per cent off `--muted` |
| `#e6e9ee` | `.dev-figs b` | 1 per cent off `--fg` |
| `#cfd2da` | `#detail .summary` | a deliberate step below `--fg` |

Three of those four are accidents of hand-tuning and should collapse into
`--muted` and `--fg`. `#cfd2da` is doing a real job, a softer body text for long
prose, and earns `--fg-soft`.

### Glyph and edge colours

| Value | Used for | Proposed token |
|---|---|---|
| `#fff` | labels on `--accent` fills, three sites | `--on-accent` |
| `#062` | the selected tick on the `--ok` badge | `--on-ok` |
| `#1a1206` | the twin duplicate glyph on the `--warn` badge | `--on-warn` |
| `#777` | the unselected tile badge border, over a black overlay | `--badge-edge` |

### Overlays, nine untokenised `rgba()` values

| Value | Used for |
|---|---|
| `rgba(0,0,0,.55)` | tile selection badge |
| `rgba(0,0,0,.6)` | on-device badge, modal backdrop |
| `rgba(0,0,0,.66)` | twin badge |
| `rgba(255,255,255,.05)` | the "this one" row in the compare card |
| `rgba(255,255,255,.08)` | compare card row hover |
| `rgba(255,255,255,.18)` | the "used now" fill inside the capacity meter |
| `rgba(255,255,255,.8)` | text on an active system-file row |
| `rgba(51,209,122,.55)` | lamp on glow |
| `rgba(224,82,82,.5)` | lamp trouble glow |

These want a scale: `--scrim-1` through `--scrim-3` for the blacks and
`--tint-1` through `--tint-3` for the whites.

## 4. Type and space, as they are

The port keeps these values. Naming them is the change; rationalising them is
not, because the look is held constant.

| Token | Value | Used for |
|---|---|---|
| `--text-xs` | 10px | tile on-device badge |
| `--text-sm` | 11px | facet headings, small counts, dev figure labels, installed paths |
| `--text-base-sm` | 12px | captions, chips, pills, muted rows, table headers |
| `--text-body-sm` | 13px | tables, detail meta, summary, stat rows |
| `--text-body` | 14px | the document base |
| `--text-lg` | 15px | card headings |
| `--text-xl` | 17px | page headings |
| `--text-2xl` | 18px | the detail panel title |

11 px and 12 px are both doing "small" and 13 px and 14 px are both doing
"body". Collapsing them is a visible change, so it is offered and not taken.

| Radii in use | Where |
|---|---|
| 2px | slider track |
| 3px | list row thumbnail, progress bar |
| 4px | facet row, on-device badge, compare card thumbnail |
| 5px | capacity meter |
| 6px | buttons, inputs, selects, tile badge, system-file rows |
| 8px | tiles, cards, panels, toast, plan lists |
| 10px | cards, pills, compare card |
| 12px | chips, modal |
| 20px | the search field |
| 50% | lamps, dots, selection badge, spinner |
| 999px | the version picker select |
| `8px 8px 0 0` and `0 0 8px 8px` | the suggestion group header and body |

The one layout constant in the token set, `--tile`, is written at runtime by the
tile-size slider. Gap is hardcoded twice: `14px` in the CSS grid and `V.gap = 14`
in `app.js`, which the windowing arithmetic depends on. Two definitions of one
number, and the rebuild must have one.

## 5. Contrast, measured

31 pairs taken from the real rule bodies, listed in
`_tools/contrast-pairs.txt`. **22 pass, 9 fail.** Reproduce with:

```
python _tools/contrast.py ROM-Sync/ui/app.css --pairs _tools/contrast-pairs.txt --strict
```

which exits 1 while any pair fails.

### Passing, text at 4.5:1

| Pair | Ratio |
|---|---|
| `--fg` on `--bg` | 15.01 |
| `--fg` on `--bg2` | 13.77 |
| `--fg` on `--bg3` | 12.23 |
| `#cfd2da` detail summary on `--bg2` | 11.26 |
| `#fff` toast text on `#2a3a5c` | 11.30 |
| `--fg` on `#2a3a5c` | 9.14 |
| `#1a1206` twin glyph on `--warn` | 9.83 |
| `--warn` on `--bg2` | 9.03 |
| `--ok` on `--bg2` | 8.43 |
| `#ffd98a` on `#4d3d1f` | 7.76 |
| `#8ef0b4` on `#1f4d33` | 7.05 |
| `#ff9aa0` on `#4d1f24` | 6.75 |
| `#e6e9ee` device figure value on `--bg2` | 13.99 |
| `#9aa3ad` on `--bg2` | 6.66 |
| `--muted` on `--bg` | 5.83 |
| `#8b939d` on `--bg2` | 5.48 |
| `--muted` on `--bg2` | 5.35 |
| `--accent` on `--bg2` | 5.29 |
| `--bad` on `--bg2` | 5.11 |
| `--muted` on `--bg3` | 4.75 |

`--muted` on `--bg3` at 4.75 is the thinnest margin in the set. Any darkening of
`--muted` or lightening of `--bg3` breaks it.

### Passing, non-text at 3:1

| Pair | Ratio |
|---|---|
| lamp on `#33d17a` on `--bg2` | 8.55 |
| lamp trouble `#e05252` on `--bg2` | 4.46 |

### Failing

| Pair | Ratio | Needs | Sites |
|---|---|---|---|
| `#fff` on `--accent` | **3.22** | 4.5 | `button.primary`, `.seg button.active`, `.sf-row.active` |
| `#062` tick on `--ok` | **3.56** | 4.5 | the tile selection badge |
| `--line` on `--bg` | **1.45** | 3.0 | controls on the page background |
| `--line` on `--bg2` | **1.33** | 3.0 | every button, input and select boundary on a panel |
| `--line` on `--bg3` | **1.18** | 3.0 | controls on a raised surface: the worst case, and the one that sets the corrected value |
| `--bg3` meter track on `--bg2` | **1.13** | 3.0 | the capacity meter and progress bars |
| lamp off `#3a3f47` on `--bg2` | **1.61** | 3.0 | the offline device lamp |

Nine failures across six distinct causes: one fill too light for a white label
(three sites), one glyph, the control border (three surfaces), the meter track
and the offline lamp.

### Corrections, fixing the right variable

The naive fix for white-on-accent is to darken the label, which the arithmetic
offers as `#292929`. That is wrong: it destroys the design. The right variable
is the fill.

| Failure | Correction | Result | Visual consequence |
|---|---|---|---|
| `#fff` on `--accent` | new `--accent-solid: #1f6cff`, used only for filled surfaces; `--accent` stays `#4f8cff` for text, borders and progress fills where it already passes | 4.52 | primary buttons and active segments go one step deeper blue; nothing else moves |
| `#062` tick on `--ok` | `--on-ok: #00541c` | 4.55 | imperceptible: a darker green on a 22 px badge |
| `--line` at 1.18, 1.33 and 1.45 | **split the token.** `--divider: #2e323c` keeps the current value for decorative rules, table lines and section separators, which 1.4.11 exempts. New `--border: #666f85` for control boundaries, where it is required | 3.69 on `--bg`, 3.39 on `--bg2`, 3.01 on `--bg3` | **this one is visible.** Button, input and select edges go from nearly invisible to clearly drawn. It is the single largest change in the correction set, and it is one token to revert |
| `--bg3` meter track | no change to the fill. The meter already carries a 1 px border, so once that border is `--border` the component is identifiable | 3.39 | none beyond the border change |
| lamp off `#3a3f47` | `--lamp-off: #5f6875` | 3.02 | the offline lamp becomes a visible grey disc rather than a near-invisible one, which is the point |

`#666f85` is derived from the worst case, `--bg3` at 1.18, and therefore
reaches 3:1 on all three surface tokens, so one border token serves
everywhere. It measures 2.25 against `#2a3a5c`, the selected-row surface, but no
bordered control sits on that surface, so the gap is theoretical.

### Focus, which does not exist yet

There is no `:focus` or `:focus-visible` rule in the stylesheet, so keyboard
focus is whatever the browser draws by default over custom button faces.

| Candidate ring | `--bg` | `--bg2` | `--bg3` | selected | `--accent-solid` |
|---|---|---|---|---|---|
| `--accent` `#4f8cff` | 5.77 | 5.29 | 4.70 | 3.51 | 1.40 |
| `#8ab4ff` | 8.89 | 8.15 | 7.24 | 5.41 | 2.16 |
| `#fff` | 18.56 | 17.03 | 15.13 | 11.30 | 4.52 |

Neither blue reaches 3:1 against a filled primary button. The fix is standard:
a 2 px ring in `--focus: #8ab4ff` with a 2 px offset in the surrounding surface
colour, so the ring is always measured against the page rather than the button
fill. One token, every control, including the primary button.

## 6. The token set the rebuild starts from

As-is values preserved, failures corrected, every literal named.

| Group | Tokens |
|---|---|
| Surface | `--bg`, `--bg2`, `--bg3`, `--surface-selected`, `--surface-chip-hover`, `--surface-danger` |
| Line | `--divider` (decorative), `--border` (control, 3:1) |
| Text | `--fg`, `--fg-soft`, `--muted`, `--on-accent`, `--on-ok`, `--on-warn` |
| Status | `--accent`, `--accent-solid`, `--ok`, `--warn`, `--bad` |
| Pill | three background and foreground pairs |
| Chip | `--chip` plus six kind surfaces |
| Lamp | three fills and three rings |
| Overlay | `--scrim-1` to `--scrim-3`, `--tint-1` to `--tint-3` |
| Focus | `--focus` |
| Type | eight sizes, 10 px to 18 px |
| Radius | eleven values plus two compounds |
| Layout | `--tile`, `--grid-gap` (one definition, read by both the CSS and the windowing arithmetic) |

Two properties the current stylesheet does not have and the rebuild adds,
because they are requirements rather than taste: a `prefers-reduced-motion`
block that stops the spinner animation, and the focus token above. There is no
light theme and none is planned, so `prefers-color-scheme` stays absent by
decision rather than by omission.
