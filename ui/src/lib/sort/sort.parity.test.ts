/** Version 1's sort keys for all 74 synthetic games, and its seven orders (six plus the fallback). */
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { readFixture } from '../../../parity/fixture/fixture.ts'
import { asListed, syntheticLibrary } from '../../../parity/library/library.ts'
import { prepare } from '../game/game'
import { sorted } from './sort'

type Key = { id: number; title: string; sortTitle: string; sortKey: string; sysKey: string }
const cases = readFixture(join(import.meta.dirname, '__fixtures__/sort.v1.json')).cases as {
  keys: Key[]
  orders: Record<string, number[]>
}
const { systems, games } = syntheticLibrary()
const library = games.map((g) => prepare(asListed(g), systems))

describe('sort parity', () => {
  it('derives every key as version 1 did', () => {
    expect(cases.keys).toHaveLength(74)
    for (const k of cases.keys) {
      const g = library.find((x) => x.id === k.id)
      expect({
        id: g?.id,
        title: g?.title,
        sortTitle: g?.sortTitle,
        sortKey: g?.sortKey,
        sysKey: g?.sysKey,
      }).toEqual(k)
    }
  })

  it('orders the library as version 1 did in every mode', () => {
    expect(Object.keys(cases.orders)).toEqual([
      'title',
      'year',
      'rating',
      'size',
      'system',
      'mtime',
      'unknown-mode',
    ])
    for (const [mode, ids] of Object.entries(cases.orders))
      expect(
        sorted(library, mode).map((g) => g.id),
        mode,
      ).toEqual(ids)
  })
})
