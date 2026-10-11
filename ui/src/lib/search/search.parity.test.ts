/** Version 1's parseQuery and passesQuery, reproduced on all 62 queries over the synthetic library. */
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { readFixture } from '../../../parity/fixture/fixture.ts'
import { asListed, syntheticLibrary } from '../../../parity/library/library.ts'
import { prepare } from '../game/game'
import { matchesQuery, parseQuery } from './search'

type Case = { q: string; parsed: unknown; matches: number[] }
const cases = readFixture(join(import.meta.dirname, '__fixtures__/grammar.v1.json')).cases as Case[]

const { systems, games } = syntheticLibrary()
const library = games.map((g) => prepare(asListed(g), systems))

describe('search parity', () => {
  it('parses every query as version 1 did', () => {
    expect(cases).toHaveLength(62)
    for (const c of cases) expect(parseQuery(c.q), c.q).toEqual(c.parsed)
  })

  it('matches the same games for every query', () => {
    for (const c of cases) {
      const q = parseQuery(c.q)
      expect(
        library.filter((g) => matchesQuery(g, q)).map((g) => g.id),
        c.q,
      ).toEqual(c.matches)
    }
  })
})
