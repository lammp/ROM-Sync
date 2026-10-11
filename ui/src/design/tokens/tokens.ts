/**
 * Every design token, in one place (F11-S2).
 *
 * Values are version 1's, from `docs/design/CAPTURE-TOKENS.md`, with the
 * section 6 corrections applied: `--line` is split into `--divider` and
 * `--border`, filled surfaces take `--accent-solid`, and the offline lamp,
 * the selected tick and the focus ring take the values that pass WCAG 2.2.
 * `tokens.css` is generated from this module by `npm run tokens` and is
 * never edited by hand; `tokens.test.ts` fails when the two disagree.
 */

/** Colours, grouped by the job they do. Each key is the custom property. */
export const COLOUR = {
  // Surface
  '--bg': '#121317',
  '--bg2': '#1a1c22',
  '--bg3': '#23262e',
  '--surface-selected': '#2a3a5c',
  '--surface-chip-hover': '#3a4260',
  '--surface-danger': '#3a2226',
  // Line: decorative rules are exempt from 1.4.11; control boundaries are not
  '--divider': '#2e323c',
  '--border': '#666f85',
  '--badge-edge': '#777777',
  // Text
  '--fg': '#e6e7ea',
  '--fg-soft': '#cfd2da',
  '--muted': '#8b90a0',
  '--on-accent': '#ffffff',
  '--on-ok': '#00541c',
  '--on-warn': '#1a1206',
  // Status
  '--accent': '#4f8cff',
  '--accent-solid': '#1f6cff',
  '--ok': '#3ccf7a',
  '--warn': '#f0b23d',
  '--bad': '#f2575d',
  // Pill
  '--pill-ok-bg': '#1f4d33',
  '--pill-ok-fg': '#8ef0b4',
  '--pill-warn-bg': '#4d3d1f',
  '--pill-warn-fg': '#ffd98a',
  '--pill-bad-bg': '#4d1f24',
  '--pill-bad-fg': '#ff9aa0',
  // Chip
  '--chip': '#2b3040',
  '--chip-system': '#2f4a3a',
  '--chip-franchise': '#4a2f4a',
  '--chip-suggested': '#4a3f2f',
  '--chip-collection': '#3d2f4a',
  '--chip-theme': '#2f3a4a',
  '--chip-mode': '#2f4a48',
  // Lamp: red only for a device in trouble, never for one merely unplugged
  '--lamp-off': '#5f6875',
  '--lamp-off-ring': '#4a505a',
  '--lamp-on': '#33d17a',
  '--lamp-on-ring': '#2aa35f',
  '--lamp-on-glow': 'rgba(51, 209, 122, 0.55)',
  '--lamp-bad': '#e05252',
  '--lamp-bad-ring': '#b83c3c',
  '--lamp-bad-glow': 'rgba(224, 82, 82, 0.5)',
  // Overlay
  '--scrim-1': 'rgba(0, 0, 0, 0.55)',
  '--scrim-2': 'rgba(0, 0, 0, 0.6)',
  '--scrim-3': 'rgba(0, 0, 0, 0.66)',
  '--tint-1': 'rgba(255, 255, 255, 0.05)',
  '--tint-2': 'rgba(255, 255, 255, 0.08)',
  '--tint-3': 'rgba(255, 255, 255, 0.18)',
  // Focus: a 2 px ring with a 2 px offset in the surrounding surface
  '--focus': '#8ab4ff',
} as const

/** Type sizes: version 1's eight, named rather than rationalised. */
export const TEXT = {
  '--text-xs': '10px',
  '--text-sm': '11px',
  '--text-base-sm': '12px',
  '--text-body-sm': '13px',
  '--text-body': '14px',
  '--text-lg': '15px',
  '--text-xl': '17px',
  '--text-2xl': '18px',
} as const

/** Radii: eleven values and the two compounds of the suggestion group. */
export const RADIUS = {
  '--radius-2': '2px',
  '--radius-3': '3px',
  '--radius-4': '4px',
  '--radius-5': '5px',
  '--radius-6': '6px',
  '--radius-8': '8px',
  '--radius-10': '10px',
  '--radius-12': '12px',
  '--radius-20': '20px',
  '--radius-round': '50%',
  '--radius-pill': '999px',
  '--radius-top': '8px 8px 0 0',
  '--radius-bottom': '0 0 8px 8px',
} as const

/** Grid geometry in pixels, read by both the stylesheet and the windowing arithmetic. */
export const TILE = 150
/** The tile slider's range, version 1's 90 to 260 px. */
export const TILE_MIN = 90
export const TILE_MAX = 260
export const GRID_GAP = 14

export const LAYOUT = {
  '--tile': `${TILE}px`,
  '--grid-gap': `${GRID_GAP}px`,
} as const

export const TOKENS = { ...COLOUR, ...TEXT, ...RADIUS, ...LAYOUT } as const

export type ColourToken = keyof typeof COLOUR
export type TextToken = keyof typeof TEXT
export type RadiusToken = keyof typeof RADIUS
export type LayoutToken = keyof typeof LAYOUT
export type Token = keyof typeof TOKENS

/** A `var()` reference to a token, checked against the set at compile time. */
export function cssVar(name: Token): `var(${Token})` {
  return `var(${name})`
}

const HEADER = '/* Generated from tokens.ts by `npm run tokens`. Do not edit. */'

/** The stylesheet `tokens.css` must hold, byte for byte. */
export function stylesheet(): string {
  const groups = [COLOUR, TEXT, RADIUS, LAYOUT]
  const body = groups
    .map((group) =>
      Object.entries(group)
        .map(([name, value]) => `  ${name}: ${value};`)
        .join('\n'),
    )
    .join('\n\n')
  return `${HEADER}\n:root {\n${body}\n}\n`
}
