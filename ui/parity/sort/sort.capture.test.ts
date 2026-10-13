import { describe, expect, test } from 'vitest'
import { readFixture } from '../fixture/fixture.ts'
import { FIXTURE, captureSort, type SortCases } from './sort.capture.ts'

const fixture = (): SortCases => readFixture(FIXTURE).cases as SortCases
const key = (title: string): string => {
  const found = fixture().keys.find((k) => k.title === title)
  if (!found) throw new Error(`no ${title}`)
  return found.sortKey
}

describe('sort capture', () => {
  test('keys', async () => {
    const { header, cases } = readFixture(FIXTURE)
    expect(header.corpus).toBe('sort')
    expect(cases).toEqual(await captureSort())
    expect(key('Mega Man 2') < key('Mega Man 10')).toBe(true)
    expect(key('Pokémon Red')).toBe('pokemon red')
    expect(key('The Legend of Zelda')).toBe('legend of zelda')
  })

  test('orders', () => {
    const { orders, keys } = fixture()
    expect(Object.keys(orders)).toEqual([
      'title',
      'year',
      'rating',
      'size',
      'system',
      'mtime',
      'unknown-mode',
    ])
    for (const order of Object.values(orders))
      expect([...order].sort((a, b) => a - b)).toEqual(keys.map((k) => k.id).sort((a, b) => a - b))
  })

  test('scale', () => {
    const { scale } = fixture()
    expect(scale.toBytes.find((s) => s.slider === 0)?.bytes).toBeNull()
    expect(scale.toBytes.find((s) => s.slider === 1000)?.bytes).toBeNull()
    expect(scale.toSlider.find((s) => s.bytes === null)?.slider).toBeNull()
  })
})
