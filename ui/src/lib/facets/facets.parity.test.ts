/**
 * Version 1's facet lists, reproduced over all 18 captured filter states:
 * values, labels, counts, order, the fold at ten, the cap at sixty, chosen
 * values kept at zero, and the more and less markers.
 *
 * One declared deviation (REBUILD-UI section 10): a chosen value past the
 * cap is listed. The state that chooses one is checked for exactly that
 * difference and no other.
 */
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { readFixture } from '../../../parity/fixture/fixture.ts'
import { asListed, syntheticLibrary } from '../../../parity/library/library.ts'
import { prepare } from '../game/game'
import { parseQuery } from '../search/search'
import { FACETS, entries, filter, fold, type Chosen, type Facet, type Ranges } from './facets'

type State = {
  name: string
  q?: string
  sets?: Partial<Record<Facet, string[]>>
  ranges?: Record<string, number | boolean | null>
  expanded?: Facet[]
}
type Row =
  | { v: string; label: string; n: number; on: boolean; zero: boolean }
  | { more: string; label: string; n: string }
  | { empty: string }
type Case = { state: State; shown: number[]; facets: Record<Facet, Row[]> }

const cases = readFixture(join(import.meta.dirname, '__fixtures__/facets.v1.json')).cases as Case[]
const { systems, games } = syntheticLibrary()
const library = games.map((g) => prepare(asListed(g), systems))
const none = { isSelected: () => false, onDevice: () => false }

function rangesOf(r: State['ranges'] = {}): Ranges {
  const n = (k: string) => (r[k] as number | null | undefined) ?? null
  return {
    size: { min: n('sizeMin'), max: n('sizeMax') },
    year: { min: n('yearMin'), max: n('yearMax') },
    rating: n('rating') ?? 0,
    flags: {
      matched: r.matched === true,
      selected: r.selected === true,
      ondevice: r.ondevice === true,
      folder: r.folder === true,
    },
  }
}

/** The rows version 1 drew for a facet, from this module's lists. */
function draw(state: State) {
  const chosen = Object.fromEntries(
    FACETS.map((f) => [f, state.sets?.[f] ?? []]),
  ) as unknown as Chosen
  const filtered = filter(library, parseQuery(state.q ?? ''), rangesOf(state.ranges), chosen, none)
  const facets = Object.fromEntries(
    FACETS.map((facet) => {
      const { shown, hidden, less } = fold(
        entries(facet, filtered, chosen),
        (state.expanded ?? []).includes(facet),
      )
      const rows: Row[] = shown.map((e) => ({
        v: e.value,
        label: facet === 'system' ? systems[e.value] || e.value : e.value,
        n: e.count,
        on: e.chosen,
        zero: e.count === 0,
      }))
      if (rows.length === 0) rows.push({ empty: '—' })
      if (hidden > 0) rows.push({ more: '1', label: 'more…', n: `+${hidden}` })
      else if (less) rows.push({ more: '0', label: 'less…', n: '' })
      return [facet, rows]
    }),
  ) as Record<Facet, Row[]>
  return { shown: filtered.shown.map((g) => g.id), facets }
}

const PAST_THE_CAP = 'a tag past the cap'

describe('facets parity', () => {
  it('covers all 18 states', () => {
    expect(cases).toHaveLength(18)
  })

  it('shows the same games in every state', () => {
    // Order is the sort's (F11-S16); here the set is what the filter decides.
    for (const c of cases)
      expect(
        [...draw(c.state).shown].sort((a, b) => a - b),
        c.state.name,
      ).toEqual([...c.shown].sort((a, b) => a - b))
  })

  it('draws every facet as version 1 did', () => {
    for (const c of cases.filter((c) => c.state.name !== PAST_THE_CAP)) {
      const ours = draw(c.state).facets
      for (const facet of FACETS)
        expect(ours[facet], `${c.state.name}: ${facet}`).toEqual(c.facets[facet])
    }
  })

  it('lists a chosen value past the cap, the one declared deviation', () => {
    const c = cases.find((c) => c.state.name === PAST_THE_CAP)
    expect(c).toBeDefined()
    if (!c) return
    const ours = draw(c.state).facets
    for (const facet of FACETS.filter((f) => f !== 'tag'))
      expect(ours[facet], facet).toEqual(c.facets[facet])
    const theirs = c.facets.tag
    expect(theirs.some((r) => 'v' in r && r.v === 'Tag 70')).toBe(false)
    const extra = ours.tag.filter(
      (r) => !theirs.some((t) => JSON.stringify(t) === JSON.stringify(r)),
    )
    expect(extra).toEqual([expect.objectContaining({ v: 'Tag 70', on: true })])
    expect(ours.tag.filter((r) => r !== extra[0])).toEqual(theirs)
  })
})
