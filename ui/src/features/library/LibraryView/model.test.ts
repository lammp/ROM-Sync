import { describe, expect, it, vi } from 'vitest'
import { freshWorld } from '../../../../e2e/fake/world'
import { SLIDER_MAX } from '../../../lib/scale/scale'
import { onDeviceKeys } from '../../../lib/selection/selection'
import { catalogue } from '../../../queries/library/library'
import { EMPTY, type FilterValues } from '../../../store/slices/filters/filters'
import {
  YEAR_MAX,
  YEAR_MIN,
  chips,
  facetViews,
  narrow,
  selectionCounts,
  sizeBounds,
  sizeFromPair,
  sizeFromText,
  sizePair,
  yearFromPair,
  yearFromText,
  yearPair,
  type DeviceState,
} from './model'

const world = freshWorld()
const { games, systems } = catalogue(world.games, world.systems)
const device: NonNullable<DeviceState> = {
  selection: { modes: { snes: 'all', gba: 'none' }, overrides: { '2': true, '5': false } },
  onDevice: onDeviceKeys([{ system: 'snes', name: games[0]?.name ?? '' }]),
}
const values = (over: Partial<FilterValues>): FilterValues => ({ ...EMPTY, ...over })

describe('the library page model', () => {
  it('sorts, then filters by query, facets, ranges and flags', () => {
    const all = narrow(games, EMPTY, null)
    expect(all.filtered.shown).toHaveLength(40)
    expect(all.order.map((g) => g.title)).toEqual(
      [...all.order.map((g) => g.title)].sort((a, b) => a.localeCompare(b)),
    )
    const snes = narrow(games, values({ chosen: { ...EMPTY.chosen, system: ['snes'] } }), null)
    expect(snes.filtered.shown.every((g) => g.system === 'snes')).toBe(true)
    const found = narrow(games, values({ query: 'galaxy' }), null)
    expect(found.filtered.shown.length).toBeGreaterThan(0)
    expect(found.filtered.shown.every((g) => g.hay.includes('galaxy'))).toBe(true)
  })

  it('reads the selected and on-device flags from the device in view, and nothing without one', () => {
    const flags = { ...EMPTY.flags, selected: true }
    const chosen = narrow(games, values({ flags }), device).filtered.shown
    expect(chosen.map((g) => g.id).sort((a, b) => a - b)).toEqual([
      1, 2, 9, 13, 17, 21, 25, 29, 33, 37,
    ])
    expect(narrow(games, values({ flags }), null).filtered.shown).toHaveLength(0)
    const there = narrow(games, values({ flags: { ...EMPTY.flags, ondevice: true } }), device)
    expect(there.filtered.shown.map((g) => g.id)).toEqual([1])
  })

  it('lists each facet in order, naming systems, folded and collapsed as the store says', () => {
    const { filtered } = narrow(games, EMPTY, null)
    const views = facetViews(filtered, EMPTY, [], ['genre'], systems)
    expect(views.map((v) => v.facet)).toEqual([
      'system',
      'genre',
      'franchise',
      'theme',
      'mode',
      'perspective',
      'tag',
      'decade',
      'region',
    ])
    expect(views[0]?.rows.map((r) => r.label)).toContain('Super Nintendo')
    expect(views[1]?.collapsed).toBe(true)
    expect(views[0]?.collapsed).toBe(false)
  })

  it('makes a chip of every filter in force, each removing only itself', () => {
    const c = { toggle: vi.fn(), clearSize: vi.fn(), clearYear: vi.fn(), clearRating: vi.fn() }
    const f = values({
      chosen: { ...EMPTY.chosen, system: ['snes'], genre: ['Racing'] },
      size: { min: 1024 * 1024, max: null },
      year: { min: 1990, max: 1999 },
      rating: 80,
    })
    const list = chips(f, systems, c)
    expect(list.map((x) => x.label)).toEqual([
      'Super Nintendo',
      'Racing',
      'size ≥ 1.00 MB',
      'year 1990–1999',
      'rating ≥ 80',
    ])
    list[0]?.onRemove()
    expect(c.toggle).toHaveBeenCalledWith('system', 'snes')
    list[2]?.onRemove()
    list[3]?.onRemove()
    list[4]?.onRemove()
    expect([c.clearSize, c.clearYear, c.clearRating].map((s) => s.mock.calls.length)).toEqual([
      1, 1, 1,
    ])
    expect(chips(EMPTY, systems, c)).toEqual([])
  })

  it('sets the size thumbs on the library’s log scale, a missing bound at its end', () => {
    const b = sizeBounds(games)
    expect(sizePair(EMPTY, b)).toEqual({ lo: 0, hi: SLIDER_MAX })
    expect(sizeFromPair({ lo: 0, hi: SLIDER_MAX }, b)).toEqual({ min: null, max: null })
    const mid = sizeFromPair({ lo: 500, hi: SLIDER_MAX }, b)
    expect(mid.min).toBeGreaterThan(0)
    expect(sizePair(values({ size: { min: mid.min, max: null } }), b).lo).toBe(500)
    expect([sizeFromText(''), sizeFromText('  '), sizeFromText('10mb')]).toEqual([
      null,
      null,
      10 * 1024 * 1024,
    ])
  })

  it('treats the year slider’s ends as no limit, as version 1 did', () => {
    expect(yearPair(EMPTY)).toEqual({ lo: YEAR_MIN, hi: YEAR_MAX })
    expect(yearFromPair({ lo: YEAR_MIN, hi: YEAR_MAX })).toEqual({ min: null, max: null })
    expect(yearFromPair({ lo: 1990, hi: 2000 })).toEqual({ min: 1990, max: 2000 })
    expect([yearFromText(''), yearFromText('1994'), yearFromText('soon')]).toEqual([
      null,
      1994,
      null,
    ])
  })

  it('counts the selection for the summary', () => {
    const shown = games.filter((g) => g.system === 'snes')
    const counts = selectionCounts(games, shown, device)
    expect(counts.selected.n).toBe(10)
    expect(counts.shown).toEqual({ selected: 9, unselected: 1 })
    expect(counts.onDevice).toBe(1)
    expect(counts.override(games.find((g) => g.id === 5) ?? games[0]!)).toBe(true)
  })
})
