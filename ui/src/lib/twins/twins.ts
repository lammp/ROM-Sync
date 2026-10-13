/**
 * Cross-system twins: the same game on another system (version 1's
 * buildTwins, ported exactly and pinned by the F0 twin corpus).
 *
 * The key is IGDB's canonical name, falling back to the title, then the file
 * name: lower-cased, "&" read as "and", apostrophes and a few stylised
 * characters normalised, articles and "part" dropped, Roman numerals II to X
 * read as digits. Stripping a trailing release form (3D, HD, Deluxe,
 * Remastered and so on) lets "Majora's Mask 3D" meet "Majora's Mask", but
 * that strip is a guess: "Earthworm Jim 3D" is a different game. A pair that
 * meets only after the strip is marked loose, and nothing is ever resolved
 * automatically.
 */

const ROMAN: Readonly<Record<string, string>> = {
  ii: '2',
  iii: '3',
  iv: '4',
  v: '5',
  vi: '6',
  vii: '7',
  viii: '8',
  ix: '9',
  x: '10',
}
const STOP: ReadonlySet<string> = new Set(['the', 'a', 'an', 'part'])
const FORM: ReadonlySet<string> = new Set([
  '3d',
  'hd',
  'dx',
  'deluxe',
  'remaster',
  'remastered',
  'remake',
  'definitive',
  'anniversary',
  'edition',
])
const LEET: Readonly<Record<string, string>> = { '!': 'i', '@': 'a', $: 's', '^': '' }

export type Twinnable = {
  readonly id: number
  readonly system: string
  readonly igdb_name: string | null
  readonly title: string
  readonly name: string
}

export function twinWords(g: Twinnable): string[] {
  const base = [
    ...(g.igdb_name || g.title || g.name || '')
      .toLowerCase()
      .replace(/&/g, 'and')
      .replace(/'/g, ''),
  ]
    .map((ch) => LEET[ch] ?? ch)
    .join('')
  return base
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .split(' ')
    .filter((w) => w && !STOP.has(w))
    .map((w) => ROMAN[w] ?? w)
}

/** The exact key: every word kept. */
export function twinKey(g: Twinnable): string {
  return twinWords(g).join('')
}

/** The loose key: trailing release forms dropped, one word always kept. */
export function twinKeyLoose(g: Twinnable): string {
  const w = twinWords(g)
  while (w.length > 1 && FORM.has(w[w.length - 1] ?? '')) w.pop()
  return w.join('')
}

export type Twin<G> = { readonly game: G; readonly loose: boolean }

/** Each game's twins on other systems, in library order; games with none are absent. */
export function buildTwins<G extends Twinnable>(games: readonly G[]): Map<number, Twin<G>[]> {
  const exact = new Map<string, G[]>()
  const loose = new Map<string, G[]>()
  for (const g of games) {
    for (const [map, key] of [
      [exact, twinKey(g)],
      [loose, twinKeyLoose(g)],
    ] as const) {
      if (!key) continue
      const group = map.get(key)
      if (group) group.push(g)
      else map.set(key, [g])
    }
  }
  const exactOf = new Map<number, G[]>()
  for (const group of exact.values()) for (const g of group) exactOf.set(g.id, group)
  const twins = new Map<number, Twin<G>[]>()
  for (const group of loose.values()) {
    if (group.length < 2) continue
    for (const g of group) {
      const mine = new Set((exactOf.get(g.id) ?? []).map((x) => x.id))
      const others = group
        .filter((o) => o.id !== g.id && o.system !== g.system)
        .map((o) => ({ game: o, loose: !mine.has(o.id) }))
      if (others.length) twins.set(g.id, others)
    }
  }
  return twins
}
