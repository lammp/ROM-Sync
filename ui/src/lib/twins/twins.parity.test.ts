/** Version 1's twin keys and twin lists for all 74 synthetic games. */
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { readFixture } from '../../../parity/fixture/fixture.ts'
import { asListed, syntheticLibrary } from '../../../parity/library/library.ts'
import { buildTwins, twinKey, twinKeyLoose } from './twins'

type Case = {
  id: number
  title: string
  igdb: string | null
  system: string
  exact: string
  loose: string
  twins: { id: number; loose: boolean }[]
}
const cases = readFixture(join(import.meta.dirname, '__fixtures__/twins.v1.json')).cases as Case[]
const library = syntheticLibrary().games.map(asListed)
const twins = buildTwins(library)

describe('twins parity', () => {
  it('covers all 74 games', () => {
    expect(cases).toHaveLength(74)
  })

  it('keys every game and lists its twins as version 1 did', () => {
    for (const c of cases) {
      const game = library.find((x) => x.id === c.id)
      expect(game, String(c.id)).toBeDefined()
      if (!game) continue
      expect(
        {
          id: game.id,
          title: game.title,
          igdb: game.igdb_name,
          system: game.system,
          exact: twinKey(game),
          loose: twinKeyLoose(game),
          twins: (twins.get(game.id) ?? []).map((t) => ({ id: t.game.id, loose: t.loose })),
        },
        c.title,
      ).toEqual(c)
    }
  })
})
