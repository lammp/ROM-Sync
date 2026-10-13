import { describe, expect, it } from 'vitest'
import { prepare, type GameInput } from '../game/game'
import { COMPARATORS, KEYS, matchClause, matchesQuery, parseQuery } from './search'

const game = (over: Partial<GameInput> = {}) =>
  prepare(
    {
      id: 1,
      name: 'Mega Man 2 (USA)',
      title: 'Mega Man 2',
      igdb_name: 'Mega Man 2',
      system: 'nes',
      genres: ['Platform'],
      tags: { franchise: ['Mega Man'], perspective: ['Side view'] },
      region: 'USA',
      year: 1988,
      size: 262_144,
      rating: 85,
      votes: 120,
      files: 0,
      kind: 'file',
      matched: true,
      mtime: 0,
      ...over,
    },
    { nes: 'Nintendo Entertainment System' },
  )

describe('parseQuery', () => {
  it('knows 13 keys and 6 comparators', () => {
    expect(KEYS).toHaveLength(13)
    expect(COMPARATORS).toHaveLength(6)
  })

  it('splits words, keeps quoted phrases whole, and lower-cases', () => {
    expect(parseQuery('Mega "Man 2"  x').terms).toEqual(['mega', 'man 2', 'x'])
  })

  it('reads numeric, size and name clauses', () => {
    expect(parseQuery('year>=1990 rating:80 size:2mb Genre:RPG').clauses).toEqual([
      { key: 'year', op: '>=', v: 1990 },
      { key: 'rating', op: '=', v: 80 },
      { key: 'size', op: '≈', v: 2_097_152 },
      { key: 'genre', op: '~', v: 'rpg' },
    ])
  })

  it('keeps an unknown key, or a key with a space before its value, as words', () => {
    expect(parseQuery('colour:red year >1990')).toEqual({
      terms: ['colour:red', 'year', '>1990'],
      clauses: [],
    })
  })
})

describe('matching', () => {
  it('needs every term in the haystack', () => {
    expect(matchesQuery(game(), parseQuery('mega nintendo'))).toBe(true)
    expect(matchesQuery(game(), parseQuery('mega zelda'))).toBe(false)
  })

  it('compares numbers, and counts a game with no file count as one file', () => {
    expect(matchesQuery(game(), parseQuery('year<1990 rating>=85 files:1'))).toBe(true)
    expect(matchesQuery(game(), parseQuery('votes>500'))).toBe(false)
  })

  it('matches a size within 5 per cent', () => {
    expect(matchesQuery(game(), parseQuery('size:250k'))).toBe(true)
    expect(matchesQuery(game(), parseQuery('size:240k'))).toBe(false)
  })

  it('never matches a number it cannot read, or a game without the number', () => {
    expect(matchesQuery(game(), parseQuery('year>abc'))).toBe(false)
    expect(matchesQuery(game({ year: null }), parseQuery('year<3000'))).toBe(false)
    expect(matchesQuery(game(), parseQuery('size:huge'))).toBe(false)
  })

  it('matches names by containment, the system by key or label', () => {
    const g = game()
    for (const q of [
      'system:nes',
      'system:entertainment',
      'franchise:mega',
      'perspective:side',
      'region:us',
    ])
      expect(matchClause(g, parseQuery(q).clauses[0]!), q).toBe(true)
    expect(matchesQuery(g, parseQuery('theme:horror'))).toBe(false)
  })
})
