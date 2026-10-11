import { describe, expect, it } from 'vitest'
import { prepare, type GameInput } from './game'

const base: GameInput = {
  id: 1,
  name: 'Super Metroid (Japan, USA) (En,Ja)',
  title: 'Super Metroid',
  igdb_name: 'Super Metroid',
  system: 'snes',
  genres: ['Platform', 'Adventure'],
  tags: { franchise: ['Metroid'], mode: ['Single player'], collection: ['Favourites'] },
  region: 'Japan, USA',
  year: 1994,
  size: 3_145_728,
  rating: 93,
  votes: 400,
  files: 1,
  kind: 'file',
  matched: true,
  mtime: 0,
}

describe('prepare', () => {
  it('labels the system from the systems map, else by its key', () => {
    expect(prepare(base, { snes: 'Super Nintendo' }).sysLabel).toBe('Super Nintendo')
    expect(prepare(base, {}).sysLabel).toBe('snes')
  })

  it('derives the decade, or none without a year', () => {
    expect(prepare(base, {}).decade).toBe('1990s')
    expect(prepare({ ...base, year: null }, {}).decade).toBeNull()
  })

  it('splits regions and drops empties', () => {
    expect(prepare(base, {}).regions).toEqual(['Japan', 'USA'])
    expect(prepare({ ...base, region: ' , ' }, {}).regions).toEqual([])
    expect(prepare({ ...base, region: null }, {}).regions).toEqual([])
  })

  it('sorts tags into the four facet kinds and the rest', () => {
    const g = prepare(base, {})
    expect(g.kinds).toEqual({
      franchise: ['Metroid'],
      theme: [],
      mode: ['Single player'],
      perspective: [],
      other: ['Favourites'],
    })
    expect(g.otherTags).toEqual(['Favourites'])
    expect(g.tagNames).toEqual(['Metroid', 'Single player', 'Favourites'])
  })

  it('builds the haystack from every searchable name, lower-cased', () => {
    expect(prepare(base, { snes: 'Super Nintendo' }).hay).toBe(
      'super metroid | super metroid (japan, usa) (en,ja) | super metroid | super nintendo | snes | platform | adventure | metroid | single player | favourites | japan | usa',
    )
  })

  it('leaves out a missing canonical name', () => {
    expect(prepare({ ...base, igdb_name: null, genres: [], tags: {}, region: null }, {}).hay).toBe(
      'super metroid | super metroid (japan, usa) (en,ja) | snes | snes',
    )
  })
})
