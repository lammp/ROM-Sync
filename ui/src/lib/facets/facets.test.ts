import { describe, expect, it } from 'vitest'
import { prepare, type GameInput } from '../game/game'
import { parseQuery } from '../search/search'
import {
  FACETS,
  FACET_CAP,
  FACET_SHOW,
  entries,
  facetFail,
  filter,
  fold,
  passesRanges,
  type Chosen,
  type Entry,
  type Ranges,
} from './facets'

const game = (id: number, over: Partial<GameInput> = {}) =>
  prepare(
    {
      id,
      name: `g${id}`,
      title: `Game ${id}`,
      igdb_name: null,
      system: 'nes',
      genres: ['Platform'],
      tags: {},
      region: 'USA',
      year: 1990,
      size: 1000,
      rating: 70,
      votes: 10,
      files: 1,
      kind: 'file',
      matched: true,
      mtime: 0,
      ...over,
    },
    {},
  )

const nothing = Object.fromEntries(FACETS.map((f) => [f, []])) as unknown as Chosen
const choose = (over: Partial<Chosen>): Chosen => ({ ...nothing, ...over })
const open: Ranges = {
  size: { min: null, max: null },
  year: { min: null, max: null },
  rating: 0,
  flags: { matched: false, selected: false, ondevice: false, folder: false },
}
const none = { isSelected: () => false, onDevice: () => false }
const all = parseQuery('')

describe('facetFail', () => {
  it('names the one facet a game fails, or many', () => {
    const g = game(1)
    expect(facetFail(g, nothing)).toBeNull()
    expect(facetFail(g, choose({ system: ['snes'] }))).toBe('system')
    expect(facetFail(g, choose({ system: ['snes'], genre: ['RPG'] }))).toBe('many')
    expect(facetFail(g, choose({ system: ['nes', 'snes'], region: ['USA'] }))).toBeNull()
  })
})

describe('passesRanges', () => {
  it('holds sizes, years and the rating floor, missing values failing', () => {
    const g = game(1)
    expect(passesRanges(g, { ...open, size: { min: 1001, max: null } }, none)).toBe(false)
    expect(passesRanges(g, { ...open, year: { min: 1980, max: 1999 } }, none)).toBe(true)
    expect(
      passesRanges(game(2, { year: null }), { ...open, year: { min: 1980, max: null } }, none),
    ).toBe(false)
    expect(passesRanges(game(3, { rating: null }), { ...open, rating: 1 }, none)).toBe(false)
  })

  it('applies the four flags, the device ones through the device view', () => {
    const flags = (f: Partial<Ranges['flags']>) => ({ ...open, flags: { ...open.flags, ...f } })
    expect(passesRanges(game(1, { matched: false }), flags({ matched: true }), none)).toBe(false)
    expect(passesRanges(game(1), flags({ folder: true }), none)).toBe(false)
    expect(
      passesRanges(game(1), flags({ selected: true }), { ...none, isSelected: () => true }),
    ).toBe(true)
    expect(passesRanges(game(1), flags({ ondevice: true }), none)).toBe(false)
  })
})

describe('one pass', () => {
  const lib = [game(1), game(2, { system: 'snes' }), game(3, { system: 'snes', genres: ['RPG'] })]

  it('counts a facet over the games failing only it, so its other values stay', () => {
    const chosen = choose({ system: ['nes'] })
    const f = filter(lib, all, open, chosen, none)
    expect(f.shown.map((g) => g.id)).toEqual([1])
    expect(entries('system', f, chosen).map((e) => [e.value, e.count])).toEqual([
      ['snes', 2],
      ['nes', 1],
    ])
    expect(entries('genre', f, chosen).map((e) => [e.value, e.count])).toEqual([['Platform', 1]])
  })

  it('keeps a chosen value that no game has, at zero', () => {
    const chosen = choose({ genre: ['Puzzle'] })
    const f = filter(lib, all, open, chosen, none)
    expect(entries('genre', f, chosen).at(-1)).toEqual({ value: 'Puzzle', count: 0, chosen: true })
  })

  it('applies the search before counting', () => {
    expect(filter(lib, parseQuery('game 3'), open, nothing, none).base.map((g) => g.id)).toEqual([
      3,
    ])
  })

  it('sorts decades by name, everything else by count then name', () => {
    const lib2 = [game(1, { year: 1995 }), game(2, { year: 1985 }), game(3, { year: 1999 })]
    const f = filter(lib2, all, open, nothing, none)
    expect(entries('decade', f, nothing).map((e) => e.value)).toEqual(['1980s', '1990s'])
  })
})

describe('caps and the fold', () => {
  const many = (n: number, chosen: string[] = []): Entry[] =>
    Array.from({ length: n }, (_, i) => ({
      value: `v${i}`,
      count: n - i,
      chosen: chosen.includes(`v${i}`),
    }))

  it('shows ten, then any chosen value past them, and counts the rest as hidden', () => {
    const { shown, hidden, less } = fold(many(25, ['v20']), false)
    expect(shown.map((e) => e.value)).toEqual([
      ...Array.from({ length: FACET_SHOW }, (_, i) => `v${i}`),
      'v20',
    ])
    expect([hidden, less]).toEqual([14, false])
  })

  it('shows everything when expanded, offering less only past the fold', () => {
    expect(fold(many(25), true)).toMatchObject({ hidden: 0, less: true })
    expect(fold(many(5), true)).toMatchObject({ hidden: 0, less: false })
  })

  it('caps an open-ended facet at sixty but keeps what is chosen past the cap', () => {
    const tags = Array.from({ length: 70 }, (_, i) => `T${String(i).padStart(2, '0')}`)
    const lib = tags.map((t, i) => game(i + 1, { tags: { other: [t] } }))
    const chosen = choose({ tag: ['T69'] })
    const f = filter(lib, all, open, chosen, none)
    const list = entries('tag', f, chosen)
    expect(list).toHaveLength(FACET_CAP + 1)
    expect(list.at(-1)).toEqual({ value: 'T69', count: 1, chosen: true })
    expect(entries('tag', filter(lib, all, open, nothing, none), nothing)).toHaveLength(FACET_CAP)
  })

  it('never caps systems or decades', () => {
    const lib = Array.from({ length: 70 }, (_, i) => game(i + 1, { system: `s${i}` }))
    expect(entries('system', filter(lib, all, open, nothing, none), nothing)).toHaveLength(70)
  })
})
