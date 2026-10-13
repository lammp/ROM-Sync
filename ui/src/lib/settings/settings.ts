/**
 * A setting's value as the page edits it (F11-S34): text in the field, the
 * engine's value on save. The registry says the kind and the range; sizes
 * are typed as sizes ("512 MB"), as in the library's filters (SETTINGS.md
 * section 4), and checked here before anything is sent.
 */
import { formatBytes, parseSize } from '../format/format'

export type Kind = 'str' | 'path' | 'int' | 'float' | 'bool'
export type Scalar = string | number | boolean | null

export type Def = {
  readonly kind: string
  readonly unit: string
  readonly minimum: number | null
  readonly maximum: number | null
  readonly choices: readonly string[]
}

/**
 * A setting held in bytes is typed and shown as a size. The registry writes a
 * unit as the suffix it is shown with (" bytes", " s", "/s").
 */
export function isSize(def: Def): boolean {
  const unit = def.unit.trim()
  return def.kind === 'int' && (unit === 'bytes' || unit === 'B/s')
}

/** The text a field shows for a stored value. */
export function toText(def: Def, value: Scalar): string {
  if (value === null || typeof value === 'boolean') return ''
  if (isSize(def) && typeof value === 'number') return formatBytes(value)
  return String(value)
}

export type Parsed =
  { readonly ok: true; readonly value: Scalar } | { readonly ok: false; readonly error: string }

const within = (def: Def, n: number, shown: (n: number) => string): Parsed => {
  if (def.minimum !== null && n < def.minimum)
    return { ok: false, error: `At least ${shown(def.minimum)}` }
  if (def.maximum !== null && n > def.maximum)
    return { ok: false, error: `At most ${shown(def.maximum)}` }
  return { ok: true, value: n }
}

/** The value a field's text stands for, or what is wrong with it. */
export function fromText(def: Def, text: string): Parsed {
  const t = text.trim()
  if (def.choices.length) {
    return def.choices.includes(t)
      ? { ok: true, value: t }
      : { ok: false, error: `One of ${def.choices.join(', ')}` }
  }
  if (def.kind === 'str' || def.kind === 'path') return { ok: true, value: t }
  if (isSize(def)) {
    const n = parseSize(t)
    if (n === null) return { ok: false, error: 'A size, such as 512 MB' }
    return within(def, n, formatBytes)
  }
  const n = Number(t)
  if (t === '' || !Number.isFinite(n)) return { ok: false, error: 'A number' }
  if (def.kind === 'int' && !Number.isInteger(n)) return { ok: false, error: 'A whole number' }
  return within(def, n, String)
}

/** What a field says under it: the description, the range, and a restart when one is needed. */
export function helpText(
  def: Def & { readonly description: string; readonly restart: boolean },
): string {
  const bits = [def.description]
  if (def.minimum !== null && def.maximum !== null && !def.choices.length) {
    const shown = isSize(def) ? formatBytes : String
    const unit = isSize(def) ? '' : def.unit
    bits.push(`From ${shown(def.minimum)} to ${shown(def.maximum)}${unit}.`)
  }
  if (def.restart) bits.push('Takes effect after a restart.')
  return bits.join(' ')
}

/** A size as a choice reads: "512 MB", "1 GB", "none". */
export function sizeLabel(def: Def, n: number): string {
  if (n === 0) return 'none'
  const text = formatBytes(n).replace(/\.0+ /, ' ')
  return def.unit.trim() === 'B/s' ? `${text}/s` : text
}

const KIB = 1024

/**
 * The sizes a size setting offers as a list (F11-S51): every power of two
 * from 64 KB within the registry's bounds, nothing when there is no bound,
 * and the stored value among them however odd it is.
 */
export function sizeChoices(def: Def, current: number | null): number[] {
  if (def.minimum === null || def.maximum === null) return []
  const out = new Set<number>()
  if (def.minimum === 0) out.add(0)
  for (let n = 64 * KIB; n <= def.maximum; n *= 2) if (n >= def.minimum) out.add(n)
  if (current !== null) out.add(current)
  return [...out].sort((a, b) => a - b)
}

/** The whole numbers a short range offers as a list: 1, 2, 3, 4; the stored value among them. */
export function stepChoices(def: Def, current: number | null): number[] {
  if (def.minimum === null || def.maximum === null) return []
  const out = new Set<number>()
  for (let n = Math.ceil(def.minimum); n <= def.maximum; n++) out.add(n)
  if (current !== null) out.add(current)
  return [...out].sort((a, b) => a - b)
}
