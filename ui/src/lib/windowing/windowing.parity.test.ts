/**
 * Version 1's grid arithmetic on all 25 captured layouts: columns, row
 * height, the row window with its overscan, the spacer, the rendered count,
 * and whether a later scroll redraws.
 */
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { readFixture } from '../../../parity/fixture/fixture.ts'
import { columns, rowHeight, template, windowOf } from './windowing'

type Layout = {
  name: string
  grid: boolean
  width: number
  pad: number
  tile: number | null
  tileHeight: number
  height: number
  scroll: number
  n: number
  scrollTo?: number
}
type Drawn = {
  cols: number
  rowH: number
  first: number
  last: number
  height: string
  paddingTop: string
  template: string
  rendered: number
  empty: boolean
  redrawn?: boolean
}
type Case = { layout: Layout; first: Drawn; after: Drawn | null }

const cases = readFixture(join(import.meta.dirname, '__fixtures__/windowing.v1.json'))
  .cases as Case[]

function drawn(l: Layout, scroll: number): Drawn {
  const cols = columns(l)
  const rowH = l.n === 0 ? 0 : rowHeight(l.tileHeight, l.grid)
  const w =
    l.n === 0
      ? { first: -1, last: -1, height: 0, paddingTop: 0, start: 0, end: 0 }
      : windowOf(l.n, cols, rowH, scroll, l.height)
  return {
    cols,
    rowH,
    first: w.first,
    last: w.last,
    height: `${w.height}px`,
    paddingTop: `${w.paddingTop}px`,
    template: template(l.grid, cols),
    rendered: w.end - w.start,
    empty: l.n === 0,
  }
}

describe('windowing parity', () => {
  it('covers all 25 layouts', () => {
    expect(cases).toHaveLength(25)
  })

  it('lays out every one as version 1 did', () => {
    for (const c of cases) expect(drawn(c.layout, c.layout.scroll), c.layout.name).toEqual(c.first)
  })

  it('redraws after a scroll only when the row window moves', () => {
    for (const c of cases.filter((c) => c.after)) {
      const before = drawn(c.layout, c.layout.scroll)
      const after = drawn(c.layout, c.layout.scrollTo ?? 0)
      const redrawn = after.first !== before.first || after.last !== before.last
      expect({ ...after, redrawn }, c.layout.name).toEqual(c.after)
    }
  })
})
