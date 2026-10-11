/**
 * Facets (F11-S15): version 1's one-pass filter.
 *
 * Each game is tested once against the search and the ranges, then against
 * every facet, and records which facet it fails: none, exactly one, or many.
 * That single pass serves both the result list (games failing none) and every
 * facet's counts (a game counts toward facet F when it fails none, or only
 * F), so choosing a value never hides the other values of the same facet.
 *
 * Facet lists are sorted by count then name (decades by name), capped at 60
 * for the seven open-ended facets, fold at 10, and always show what is chosen,
 * even at a count of zero and even past the fold.
 *
 * Declared deviation (REBUILD-UI section 10): a chosen value past the cap of
 * 60 is still listed. Version 1 dropped it, so it could be neither seen nor
 * cleared from its facet.
 */
import type { Game } from '../game/game'
import { matchesQuery, type Query } from '../search/search'

export const FACETS = [
  'system',
  'genre',
  'franchise',
  'theme',
  'mode',
  'perspective',
  'tag',
  'decade',
  'region',
] as const
export type Facet = (typeof FACETS)[number]

/** How many values a folded facet shows. */
export const FACET_SHOW = 10
/** How many values an open-ended facet keeps at most. */
export const FACET_CAP = 60
const CAPPED: ReadonlySet<Facet> = new Set([
  'tag',
  'genre',
  'region',
  'franchise',
  'theme',
  'mode',
  'perspective',
])

export type Chosen = Readonly<Record<Facet, readonly string[]>>

export type Ranges = {
  readonly size: { readonly min: number | null; readonly max: number | null }
  readonly year: { readonly min: number | null; readonly max: number | null }
  readonly rating: number
  readonly flags: Readonly<Record<'matched' | 'selected' | 'ondevice' | 'folder', boolean>>
}

/** What the device knows about a game, for the two device flags. */
export type DeviceView = {
  readonly isSelected: (g: Game) => boolean
  readonly onDevice: (g: Game) => boolean
}

export function valuesOf(g: Game, facet: Facet): readonly string[] {
  switch (facet) {
    case 'system':
      return [g.system]
    case 'genre':
      return g.genres
    case 'tag':
      return g.otherTags
    case 'decade':
      return g.decade ? [g.decade] : []
    case 'region':
      return g.regions
    default:
      return g.kinds[facet]
  }
}

export type Fail = Facet | 'many' | null

/** The facet a game fails: none, the one, or many. */
export function facetFail(g: Game, chosen: Chosen): Fail {
  let fail: Fail = null
  for (const facet of FACETS) {
    const want = chosen[facet]
    if (want.length === 0) continue
    if (valuesOf(g, facet).some((v) => want.includes(v))) continue
    fail = fail === null ? facet : 'many'
  }
  return fail
}

export function passesRanges(g: Game, r: Ranges, device: DeviceView): boolean {
  if (r.size.min != null && g.size < r.size.min) return false
  if (r.size.max != null && g.size > r.size.max) return false
  if (r.year.min != null && (g.year == null || g.year < r.year.min)) return false
  if (r.year.max != null && (g.year == null || g.year > r.year.max)) return false
  if (r.rating && (g.rating == null || g.rating < r.rating)) return false
  if (r.flags.matched && !g.matched) return false
  if (r.flags.folder && g.kind !== 'folder') return false
  if (r.flags.selected && !device.isSelected(g)) return false
  if (r.flags.ondevice && !device.onDevice(g)) return false
  return true
}

export type Filtered = {
  /** Games passing everything, in the order given. */
  readonly shown: readonly Game[]
  /** Games passing the search and the ranges: the population the facets count. */
  readonly base: readonly Game[]
  readonly fails: ReadonlyMap<number, Fail>
}

/** The one pass. `games` arrive sorted, so the result needs no sort. */
export function filter(
  games: readonly Game[],
  query: Query,
  ranges: Ranges,
  chosen: Chosen,
  device: DeviceView,
): Filtered {
  const shown: Game[] = []
  const base: Game[] = []
  const fails = new Map<number, Fail>()
  for (const g of games) {
    if (!matchesQuery(g, query) || !passesRanges(g, ranges, device)) continue
    base.push(g)
    const fail = facetFail(g, chosen)
    fails.set(g.id, fail)
    if (fail === null) shown.push(g)
  }
  return { shown, base, fails }
}

export type Entry = { readonly value: string; readonly count: number; readonly chosen: boolean }

/** A facet's values with their counts: sorted, capped, chosen values kept at zero and past the cap. */
export function entries(facet: Facet, filtered: Filtered, chosen: Chosen): Entry[] {
  const counts = new Map<string, number>()
  for (const g of filtered.base) {
    const fail = filtered.fails.get(g.id)
    if (fail === null || fail === facet)
      for (const v of valuesOf(g, facet)) counts.set(v, (counts.get(v) ?? 0) + 1)
  }
  const picked = chosen[facet]
  for (const v of picked) if (!counts.has(v)) counts.set(v, 0)
  const all = [...counts.entries()]
  if (facet === 'decade') all.sort((a, b) => a[0].localeCompare(b[0]))
  else all.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  let kept = all
  if (CAPPED.has(facet) && all.length > FACET_CAP) {
    const cut = all.slice(FACET_CAP).filter(([v]) => picked.includes(v))
    kept = [...all.slice(0, FACET_CAP), ...cut]
  }
  return kept.map(([value, count]) => ({ value, count, chosen: picked.includes(value) }))
}

export type Folded = {
  readonly shown: readonly Entry[]
  /** How many values the fold hides; the "more" control shows it. */
  readonly hidden: number
  /** Expanded past the fold, so a "less" control is offered. */
  readonly less: boolean
}

/** The first ten, then any chosen value past them; everything when expanded. */
export function fold(list: readonly Entry[], expanded: boolean): Folded {
  const shown = expanded
    ? list
    : [...list.slice(0, FACET_SHOW), ...list.slice(FACET_SHOW).filter((e) => e.chosen)]
  return { shown, hidden: list.length - shown.length, less: expanded && list.length > FACET_SHOW }
}
