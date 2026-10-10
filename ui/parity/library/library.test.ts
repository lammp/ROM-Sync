import { describe, expect, test } from 'vitest'
import { ownerData, stringsIn } from '../provenance/provenance.ts'
import { syntheticLibrary } from './library.ts'

describe('library', () => {
  const { systems, games } = syntheticLibrary()

  test('carries_no_owner_data', () => {
    expect(ownerData(stringsIn({ systems, games }))).toEqual([])
  })

  test('ids_are_unique', () => {
    expect(new Set(games.map((g) => g.id)).size).toBe(games.length)
  })

  test('every_system_is_labelled', () => {
    for (const g of games) expect(systems[g.system], g.title).toBeDefined()
  })

  test('reaches_the_facet_caps', () => {
    const other = new Set(
      games.flatMap((g) => g.tags.filter((t) => t.kind === 'other').map((t) => t.tag)),
    )
    expect(other.size).toBeGreaterThan(60)
    expect(new Set(games.flatMap((g) => g.genres)).size).toBeGreaterThan(10)
    expect(new Set(games.map((g) => g.system)).size).toBeGreaterThan(10)
  })

  test('is_the_same_every_time', () => {
    expect(syntheticLibrary()).toEqual(syntheticLibrary())
  })
})
