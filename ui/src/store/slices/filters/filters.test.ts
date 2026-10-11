import { describe, expect, it } from 'vitest'
import { createStore } from 'zustand/vanilla'
import { EMPTY, FACETS, FLAGS, filtersSlice, narrowed } from './filters'

const make = () => createStore(filtersSlice)

describe('filters slice', () => {
  it('starts with nothing narrowed, sorted by title', () => {
    const f = make().getState().filters
    expect(narrowed(f)).toBe(false)
    expect(f.sort).toBe('title')
    expect(Object.keys(f.chosen)).toEqual([...FACETS])
    expect(Object.keys(f.flags)).toEqual([...FLAGS])
  })

  it('toggles a facet value in and out, leaving the other facets alone', () => {
    const store = make()
    store.getState().filters.toggle('system', 'snes')
    store.getState().filters.toggle('system', 'gba')
    expect(store.getState().filters.chosen.system).toEqual(['snes', 'gba'])
    store.getState().filters.toggle('system', 'snes')
    expect(store.getState().filters.chosen.system).toEqual(['gba'])
    expect(store.getState().filters.chosen.genre).toEqual([])
  })

  it('narrows on each kind of filter', () => {
    const cases: [string, (s: ReturnType<typeof make>) => void][] = [
      ['query', (s) => s.getState().filters.setQuery('mario')],
      ['facet', (s) => s.getState().filters.toggle('region', 'USA')],
      ['size', (s) => s.getState().filters.setRange('size', { min: 1, max: null })],
      ['year', (s) => s.getState().filters.setRange('year', { min: null, max: 1999 })],
      ['rating', (s) => s.getState().filters.setRating(70)],
      ['flag', (s) => s.getState().filters.setFlag('ondevice', true)],
    ]
    for (const [name, act] of cases) {
      const store = make()
      act(store)
      expect(narrowed(store.getState().filters), name).toBe(true)
    }
  })

  it('ignores a query of spaces, and holds the rating between 0 and 100', () => {
    const store = make()
    store.getState().filters.setQuery('   ')
    expect(narrowed(store.getState().filters)).toBe(false)
    store.getState().filters.setRating(140)
    expect(store.getState().filters.rating).toBe(100)
    store.getState().filters.setRating(-5)
    expect(store.getState().filters.rating).toBe(0)
  })

  it('clears every filter but keeps the sort and the facet layout', () => {
    const store = make()
    const f = () => store.getState().filters
    f().setSort('year')
    f().setQuery('zelda')
    f().toggle('genre', 'RPG')
    f().setFlag('matched', true)
    f().setUnfolded('genre', true)
    f().clear()
    const { query, chosen, size, year, rating, flags } = f()
    expect({ query, chosen, size, year, rating, flags, sort: f().sort }).toEqual({
      ...EMPTY,
      sort: 'year',
    })
    expect(f().expanded).toEqual(['genre'])
  })

  it('keeps the fold and the collapse as two separate choices', () => {
    const store = make()
    const f = () => store.getState().filters
    f().setUnfolded('tag', true)
    f().setUnfolded('tag', true)
    f().setCollapsed('tag', true)
    expect([f().expanded, f().collapsed]).toEqual([['tag'], ['tag']])
    f().setUnfolded('tag', false)
    expect([f().expanded, f().collapsed]).toEqual([[], ['tag']])
    f().setCollapsed('tag', false)
    expect(f().collapsed).toEqual([])
  })
})
