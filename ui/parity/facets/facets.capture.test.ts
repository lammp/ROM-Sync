import { describe, expect, test } from 'vitest'
import { readFixture } from '../fixture/fixture.ts'
import { FIXTURE, captureFacets, type FacetCase, type FacetEntry } from './facets.capture.ts'

const cases = (): FacetCase[] => readFixture(FIXTURE).cases as FacetCase[]
const named = (name: string): FacetCase => {
  const found = cases().find((c) => c.state.name === name)
  if (!found) throw new Error(`no case named ${name}`)
  return found
}
const values = (list: readonly FacetEntry[]): FacetEntry[] => list.filter((e) => e.v !== undefined)

describe('facets capture', () => {
  test('counts', async () => {
    const { header, cases: fixture } = readFixture(FIXTURE)
    expect(header.corpus).toBe('facets')
    expect(fixture).toEqual(await captureFacets())
  })

  test('ordering', () => {
    for (const c of cases()) {
      for (const [facet, list] of Object.entries(c.facets)) {
        const v = values(list)
        for (let i = 1; i < v.length; i++) {
          const a = v[i - 1]
          const b = v[i]
          if (!a || !b || a.on !== b.on) continue
          if (facet === 'decade')
            expect((a.v ?? '') <= (b.v ?? ''), `${c.state.name} ${facet}`).toBe(true)
        }
      }
    }
    const genres = values(named('nothing chosen').facets.genre ?? [])
    const counts = genres.map((e) => Number(e.n))
    expect(counts).toEqual([...counts].sort((x, y) => y - x))
  })

  test('caps', () => {
    const folded = named('nothing chosen').facets.tag ?? []
    expect(values(folded)).toHaveLength(10)
    expect(folded.at(-1)?.more).toBe('1')
    const expanded = named('tags expanded').facets.tag ?? []
    expect(values(expanded)).toHaveLength(60)
    expect(expanded.at(-1)?.more).toBe('0')
    // a chosen value past the fold of ten is still drawn
    const pastFold = named('a tag past the fold').facets.tag ?? []
    expect(values(pastFold)).toHaveLength(11)
    expect(values(pastFold).at(-1)).toMatchObject({ v: 'Tag 56', on: true })
    // version 1 defect, pinned as found: a chosen value past the cap of sixty is not drawn at all
    const pastCap = named('a tag past the cap').facets.tag ?? []
    expect(values(pastCap).some((e) => e.v === 'Tag 70')).toBe(false)
  })

  test('zero_retained', () => {
    const franchise = named('a chosen value with no games').facets.franchise ?? []
    expect(franchise).toContainEqual(
      expect.objectContaining({ v: 'Not A Franchise', n: 0, on: true, zero: true }),
    )
  })
})
