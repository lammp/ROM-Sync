/**
 * The library page's arithmetic, apart from React: the filter pass, the facet
 * lists, the chips in force, the range facets' positions, and what the
 * selection summary counts. Every rule comes from lib/; this only joins them.
 */
import type { ActiveFilter } from '../../../components/molecules/ActiveChipList/ActiveChipList'
import type { Pair } from '../../../components/molecules/RangeFacet/RangeFacet'
import {
  FACETS,
  entries,
  filter,
  fold,
  type Facet,
  type Filtered,
} from '../../../lib/facets/facets'
import { formatBytes, parseSize } from '../../../lib/format/format'
import type { Game } from '../../../lib/game/game'
import {
  bytesToSlider,
  logBounds,
  sliderToBytes,
  SLIDER_MAX,
  type LogBounds,
} from '../../../lib/scale/scale'
import { parseQuery } from '../../../lib/search/search'
import {
  deviceKey,
  isOverride,
  isSelected,
  type SelectionState,
} from '../../../lib/selection/selection'
import { sorted } from '../../../lib/sort/sort'
import type { FilterValues } from '../../../store/slices/filters/filters'

/** Version 1's year slider runs from 1975 to 2026; its ends mean no limit. */
export const YEAR_MIN = 1975
export const YEAR_MAX = 2026

export type DeviceState = {
  readonly selection: SelectionState
  readonly onDevice: ReadonlySet<string>
} | null

export type Narrowed<G extends Game> = {
  readonly order: readonly G[]
  readonly filtered: Filtered & { readonly shown: readonly G[] }
}

export function narrow<G extends Game>(
  games: readonly G[],
  f: FilterValues,
  device: DeviceState,
): Narrowed<G> {
  const order = sorted(games, f.sort)
  const view = {
    isSelected: (g: Game) => (device ? isSelected(device.selection, g) : false),
    onDevice: (g: Game) => (device ? device.onDevice.has(deviceKey(g.system, g.name)) : false),
  }
  const filtered = filter(
    order,
    parseQuery(f.query),
    { size: f.size, year: f.year, rating: f.rating, flags: f.flags },
    f.chosen,
    view,
  )
  return { order, filtered: filtered as Filtered & { shown: readonly G[] } }
}

export function facetViews(
  filtered: Filtered,
  f: FilterValues,
  unfolded: readonly Facet[],
  collapsed: readonly Facet[],
  systems: Readonly<Record<string, string>>,
) {
  return FACETS.map((facet) => {
    const { shown, hidden, less } = fold(
      entries(facet, filtered, f.chosen),
      unfolded.includes(facet),
    )
    return {
      facet,
      rows: shown.map((e) => ({
        value: e.value,
        label: facet === 'system' ? systems[e.value] || e.value : e.value,
        count: e.count,
        chosen: e.chosen,
      })),
      hidden,
      less,
      collapsed: collapsed.includes(facet),
    }
  })
}

export type Clears = {
  readonly toggle: (facet: Facet, value: string) => void
  readonly clearSize: () => void
  readonly clearYear: () => void
  readonly clearRating: () => void
}

/** Every filter in force as a chip, as version 1's renderChips listed them. */
export function chips(
  f: FilterValues,
  systems: Readonly<Record<string, string>>,
  c: Clears,
): ActiveFilter[] {
  const out: ActiveFilter[] = []
  for (const facet of FACETS)
    for (const v of f.chosen[facet])
      out.push({
        key: `${facet}:${v}`,
        label: facet === 'system' ? systems[v] || v : v,
        onRemove: () => c.toggle(facet, v),
      })
  if (f.size.min != null || f.size.max != null)
    out.push({
      key: 'size',
      label:
        `size ${f.size.min != null ? `≥ ${formatBytes(f.size.min)}` : ''} ${f.size.max != null ? `≤ ${formatBytes(f.size.max)}` : ''}`.trim(),
      onRemove: c.clearSize,
    })
  if (f.year.min != null || f.year.max != null)
    out.push({
      key: 'year',
      label: `year ${f.year.min ?? ''}–${f.year.max ?? ''}`,
      onRemove: c.clearYear,
    })
  if (f.rating) out.push({ key: 'rating', label: `rating ≥ ${f.rating}`, onRemove: c.clearRating })
  return out
}

/** The size facet's thumbs over the library's log scale; a missing bound sits at its end. */
export function sizePair(f: FilterValues, b: LogBounds): Pair {
  return {
    lo: f.size.min == null ? 0 : (bytesToSlider(f.size.min, b) ?? 0),
    hi: f.size.max == null ? SLIDER_MAX : (bytesToSlider(f.size.max, b) ?? SLIDER_MAX),
  }
}

export function sizeFromPair(p: Pair, b: LogBounds) {
  return { min: sliderToBytes(p.lo, b), max: sliderToBytes(p.hi, b) }
}

export function sizeFromText(text: string): number | null {
  return text.trim() ? parseSize(text) : null
}

export function yearPair(f: FilterValues): Pair {
  return { lo: f.year.min ?? YEAR_MIN, hi: f.year.max ?? YEAR_MAX }
}

/** Version 1's ends: the year slider at its ends means no limit. */
export function yearFromPair(p: Pair) {
  return { min: p.lo <= YEAR_MIN ? null : p.lo, max: p.hi >= YEAR_MAX ? null : p.hi }
}

export function yearFromText(text: string): number | null {
  const n = Number(text.trim())
  return text.trim() && Number.isFinite(n) ? n : null
}

export function sizeBounds(games: readonly Game[]): LogBounds {
  return logBounds(games.map((g) => g.size))
}

/** What the summary counts for the device in view. */
export function selectionCounts<G extends Game>(
  games: readonly G[],
  shown: readonly G[],
  device: NonNullable<DeviceState>,
) {
  const chosen = games.filter((g) => isSelected(device.selection, g))
  const shownSelected = shown.filter((g) => isSelected(device.selection, g)).length
  return {
    selected: { n: chosen.length, bytes: chosen.reduce((a, g) => a + g.size, 0) },
    shown: { selected: shownSelected, unselected: shown.length - shownSelected },
    onDevice: device.onDevice.size,
    override: (g: Game) => isOverride(device.selection, g),
  }
}
