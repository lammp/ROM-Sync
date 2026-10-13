/**
 * Library order (F11-S16), version 1's sort keys and six comparators.
 *
 * The title key drops a leading article, strips accents and zero-pads every
 * run of digits to eight, so "Mega Man 2" sorts before "Mega Man 10" with a
 * plain comparison and no collation. Ties in every other order fall back to
 * the title key.
 */

export const SORTS = ['title', 'year', 'rating', 'size', 'system', 'mtime'] as const
export type Sort = (typeof SORTS)[number]

/** The title as sorted: lower-cased, a leading "the", "a" or "an" dropped. */
export function sortTitle(title: string, name: string): string {
  return (title || name).toLowerCase().replace(/^(the|a|an)\s+/, '')
}

/** A plain-comparable key: accents stripped, digit runs padded to eight. */
export function sortKey(title: string): string {
  return title
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/\d+/g, (d) => d.padStart(8, '0'))
}

export type Sortable = {
  readonly sortKey: string
  readonly sysKey: string
  readonly year: number | null
  readonly rating: number | null
  readonly votes: number | null
  readonly size: number
  readonly mtime: number
}

const plain = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0)
const byKey = (a: Sortable, b: Sortable) => plain(a.sortKey, b.sortKey)

const COMPARE: Readonly<Record<Sort, (a: Sortable, b: Sortable) => number>> = {
  title: byKey,
  year: (a, b) => (b.year || 0) - (a.year || 0) || byKey(a, b),
  rating: (a, b) =>
    (b.rating || 0) - (a.rating || 0) || (b.votes || 0) - (a.votes || 0) || byKey(a, b),
  size: (a, b) => b.size - a.size || byKey(a, b),
  system: (a, b) => plain(a.sysKey, b.sysKey) || byKey(a, b),
  mtime: (a, b) => (b.mtime || 0) - (a.mtime || 0) || byKey(a, b),
}

export function isSort(mode: string): mode is Sort {
  return (SORTS as readonly string[]).includes(mode)
}

/** A sorted copy; an unknown order sorts by title. */
export function sorted<T extends Sortable>(games: readonly T[], mode: string): T[] {
  return [...games].sort(isSort(mode) ? COMPARE[mode] : COMPARE.title)
}
