import { describe, expect, test } from 'vitest'
import { readFixture } from '../fixture/fixture.ts'
import { FIXTURE, captureWindowing, type WindowCase } from './windowing.capture.ts'

type Read = {
  cols: number
  rowH: number
  first: number
  last: number
  rendered: number
  redrawn?: boolean
}
const named = (name: string): WindowCase => {
  const found = (readFixture(FIXTURE).cases as WindowCase[]).find((c) => c.layout.name === name)
  if (!found) throw new Error(`no case named ${name}`)
  return found
}

describe('windowing capture', () => {
  test('bounds', async () => {
    const { header, cases } = readFixture(FIXTURE)
    expect(header.corpus).toBe('windowing')
    expect(cases).toEqual(await captureWindowing())
  })

  test('columns_follow_width_tile_and_gap', () => {
    expect((named('width 163').first as Read).cols).toBe(1)
    expect((named('width 164').first as Read).cols).toBe(1)
    expect((named('width 328').first as Read).cols).toBe(2)
    expect((named('width 0').first as Read).cols).toBe(1)
  })

  test('two_rows_of_overscan', () => {
    const scrolled = named('scrolled 500').first as Read
    expect(scrolled.first).toBe(Math.max(0, Math.floor(500 / scrolled.rowH) - 2))
  })

  test('a_small_scroll_does_not_redraw', () => {
    expect((named('a small scroll keeps the window').after as Read).redrawn).toBe(false)
    expect((named('a long scroll moves the window').after as Read).redrawn).toBe(true)
  })
})
