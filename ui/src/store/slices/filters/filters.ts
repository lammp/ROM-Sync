/**
 * What the library is narrowed to: the search, the sort, the chosen facet
 * values, the ranges and the four flags, as version 1's `S.f` held them,
 * plus, as version 1's `FX` kept them, which facets are unfolded past their
 * fold (expanded) and which sections are collapsed: two separate choices.
 */
import type { StateCreator } from 'zustand'

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

export const FLAGS = ['matched', 'selected', 'ondevice', 'folder'] as const
export type Flag = (typeof FLAGS)[number]

export type Range = { readonly min: number | null; readonly max: number | null }

export type FilterValues = {
  readonly query: string
  readonly sort: string
  readonly chosen: Readonly<Record<Facet, readonly string[]>>
  readonly size: Range
  readonly year: Range
  readonly rating: number
  readonly flags: Readonly<Record<Flag, boolean>>
}

export type FiltersSlice = {
  readonly filters: FilterValues & {
    readonly expanded: readonly Facet[]
    readonly collapsed: readonly Facet[]
    setQuery(query: string): void
    setSort(sort: string): void
    toggle(facet: Facet, value: string): void
    setRange(name: 'size' | 'year', range: Range): void
    setRating(min: number): void
    setFlag(flag: Flag, on: boolean): void
    clear(): void
    /** Shows a facet's values past the fold, or folds them again. */
    setUnfolded(facet: Facet, unfolded: boolean): void
    /** Collapses a facet's section to its heading, or opens it. */
    setCollapsed(facet: Facet, collapsed: boolean): void
  }
}

const none = Object.fromEntries(FACETS.map((f) => [f, []])) as unknown as Record<Facet, string[]>
const off = Object.fromEntries(FLAGS.map((f) => [f, false])) as unknown as Record<Flag, boolean>

export const EMPTY: FilterValues = {
  query: '',
  sort: 'title',
  chosen: none,
  size: { min: null, max: null },
  year: { min: null, max: null },
  rating: 0,
  flags: off,
}

/** Whether any filter narrows the library; the sort does not. */
export function narrowed(f: FilterValues): boolean {
  return (
    f.query.trim() !== '' ||
    FACETS.some((k) => f.chosen[k].length > 0) ||
    [f.size, f.year].some((r) => r.min !== null || r.max !== null) ||
    f.rating > 0 ||
    FLAGS.some((k) => f.flags[k])
  )
}

/** The list with the facet in it or not, as asked. */
function toggled(list: readonly Facet[], facet: Facet, on: boolean): readonly Facet[] {
  const without = list.filter((f) => f !== facet)
  return on ? [...without, facet] : without
}

export const filtersSlice: StateCreator<FiltersSlice> = (set) => {
  const patch = (p: Partial<FiltersSlice['filters']>) =>
    set((s) => ({ filters: { ...s.filters, ...p } }))
  return {
    filters: {
      ...EMPTY,
      expanded: [],
      collapsed: [],
      setQuery: (query) => patch({ query }),
      setSort: (sort) => patch({ sort }),
      toggle: (facet, value) =>
        set((s) => {
          const now = s.filters.chosen[facet]
          const next = now.includes(value) ? now.filter((v) => v !== value) : [...now, value]
          return { filters: { ...s.filters, chosen: { ...s.filters.chosen, [facet]: next } } }
        }),
      setRange: (name, range) => patch({ [name]: range }),
      setRating: (rating) => patch({ rating: Math.min(100, Math.max(0, rating)) }),
      setFlag: (flag, on) =>
        set((s) => ({ filters: { ...s.filters, flags: { ...s.filters.flags, [flag]: on } } })),
      clear: () => set((s) => ({ filters: { ...s.filters, ...EMPTY, sort: s.filters.sort } })),
      setUnfolded: (facet, unfolded) =>
        set((s) => ({
          filters: { ...s.filters, expanded: toggled(s.filters.expanded, facet, unfolded) },
        })),
      setCollapsed: (facet, collapsed) =>
        set((s) => ({
          filters: { ...s.filters, collapsed: toggled(s.filters.collapsed, facet, collapsed) },
        })),
    },
  }
}
