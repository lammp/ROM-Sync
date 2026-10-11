/**
 * Contrast, computed (F11-S3).
 *
 * WCAG 2.2 relative luminance over sRGB, the same arithmetic as
 * `_tools/contrast.py`. A translucent colour is composited over the surface
 * it sits on before it is measured. `PAIRS` lists every foreground the
 * interface draws on every surface it draws it on, by token, so a change to a
 * token value is measured rather than trusted.
 */
import { COLOUR, type ColourToken } from '../tokens/tokens'

export type Rgba = {
  readonly r: number
  readonly g: number
  readonly b: number
  readonly a: number
}
export type Kind = 'text' | 'non-text'
export type Pair = {
  readonly label: string
  readonly fg: ColourToken
  readonly bg: ColourToken
  readonly kind: Kind
}

/** WCAG 2.2: 1.4.3 for text, 1.4.11 for the boundaries and states of controls. */
export const TARGET: Readonly<Record<Kind, number>> = { text: 4.5, 'non-text': 3 }

const HEX = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i
const RGBA = /^rgba\(\s*(\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\s*\)$/

export function parse(colour: string): Rgba {
  const hex = HEX.exec(colour)
  if (hex) {
    const [, r, g, b] = hex
    return { r: parseInt(r ?? '', 16), g: parseInt(g ?? '', 16), b: parseInt(b ?? '', 16), a: 1 }
  }
  const rgba = RGBA.exec(colour)
  if (rgba) {
    const [, r, g, b, a] = rgba
    return { r: Number(r), g: Number(g), b: Number(b), a: Number(a) }
  }
  throw new Error(`not a colour: ${colour}`)
}

/** `top` painted over an opaque `under`. */
export function composite(top: Rgba, under: Rgba): Rgba {
  const mix = (t: number, u: number) => top.a * t + (1 - top.a) * u
  return { r: mix(top.r, under.r), g: mix(top.g, under.g), b: mix(top.b, under.b), a: 1 }
}

function channel(value: number): number {
  const c = value / 255
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}

export function luminance({ r, g, b }: Rgba): number {
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

/** The contrast ratio of `fg` drawn on `bg`, from 1 to 21. */
export function ratio(fg: string, bg: string): number {
  const under = parse(bg)
  if (under.a !== 1) throw new Error(`a surface must be opaque: ${bg}`)
  const [hi, lo] = [luminance(composite(parse(fg), under)), luminance(under)].sort((x, y) => y - x)
  return ((hi ?? 0) + 0.05) / ((lo ?? 0) + 0.05)
}

/** Every surface a control can sit on, which the focus ring's offset shows. */
export const SURFACES: readonly ColourToken[] = [
  '--bg',
  '--bg2',
  '--bg3',
  '--surface-selected',
  '--surface-chip-hover',
  '--surface-danger',
]

const CHIPS: readonly ColourToken[] = [
  '--chip',
  '--surface-chip-hover',
  '--chip-system',
  '--chip-franchise',
  '--chip-suggested',
  '--chip-collection',
  '--chip-theme',
  '--chip-mode',
]

const text = (label: string, fg: ColourToken, bg: ColourToken): Pair => ({
  label,
  fg,
  bg,
  kind: 'text',
})
const edge = (label: string, fg: ColourToken, bg: ColourToken): Pair => ({
  label,
  fg,
  bg,
  kind: 'non-text',
})

export const PAIRS: readonly Pair[] = [
  ...(['--bg', '--bg2', '--bg3', '--surface-selected', '--surface-danger'] as const).map((bg) =>
    text(`body text on ${bg}`, '--fg', bg),
  ),
  text('soft prose on panel', '--fg-soft', '--bg2'),
  ...(['--bg', '--bg2', '--bg3'] as const).map((bg) => text(`muted text on ${bg}`, '--muted', bg)),
  text('accent text on panel', '--accent', '--bg2'),
  text('ok text on panel', '--ok', '--bg2'),
  text('warn text on panel', '--warn', '--bg2'),
  text('bad text on panel', '--bad', '--bg2'),
  text('ok pill', '--pill-ok-fg', '--pill-ok-bg'),
  text('warn pill', '--pill-warn-fg', '--pill-warn-bg'),
  text('bad pill and bad toast', '--pill-bad-fg', '--pill-bad-bg'),
  text('body text on a bad toast', '--fg', '--pill-bad-bg'),
  text('toast text', '--on-accent', '--surface-selected'),
  text('label on a filled control', '--on-accent', '--accent-solid'),
  text('selection tick', '--on-ok', '--ok'),
  text('twin glyph', '--on-warn', '--warn'),
  ...CHIPS.map((bg) => text(`chip text on ${bg}`, '--fg', bg)),
  ...(['--bg', '--bg2', '--bg3'] as const).map((bg) =>
    edge(`control border on ${bg}`, '--border', bg),
  ),
  edge('danger button border', '--bad', '--surface-danger'),
  edge('suggested chip outline', '--warn', '--chip-suggested'),
  edge('meter fill on its track', '--ok', '--bg3'),
  edge('lamp off on panel', '--lamp-off', '--bg2'),
  edge('lamp on on panel', '--lamp-on', '--bg2'),
  edge('lamp trouble on panel', '--lamp-bad', '--bg2'),
  ...SURFACES.map((bg) => edge(`focus ring on ${bg}`, '--focus', bg)),
]

/** The ratio a pair measures with the current token values. */
export function measure(pair: Pair): number {
  return ratio(COLOUR[pair.fg], COLOUR[pair.bg])
}

/** Every pair below its target, with what it measures. */
export function failures(pairs: readonly Pair[] = PAIRS): readonly (Pair & { ratio: number })[] {
  return pairs.map((p) => ({ ...p, ratio: measure(p) })).filter((p) => p.ratio < TARGET[p.kind])
}
