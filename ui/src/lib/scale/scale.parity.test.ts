/** Version 1's size slider in both directions, over the synthetic library's bounds. */
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { readFixture } from '../../../parity/fixture/fixture.ts'
import { syntheticLibrary } from '../../../parity/library/library.ts'
import { bytesToSlider, logBounds, sliderToBytes, type LogBounds } from './scale'

const { scale } = readFixture(join(import.meta.dirname, '../sort/__fixtures__/sort.v1.json'))
  .cases as {
  scale: {
    sizeLog: LogBounds
    toBytes: { slider: number; bytes: number | null }[]
    toSlider: { bytes: number | null; slider: number | null }[]
  }
}

describe('scale parity', () => {
  it('bounds the synthetic library as version 1 did', () => {
    const b = logBounds(syntheticLibrary().games.map((g) => g.size))
    expect(b.min).toBe(scale.sizeLog.min)
    expect(b.max).toBe(scale.sizeLog.max)
  })

  it('maps slider to bytes and bytes to slider exactly', () => {
    for (const c of scale.toBytes)
      expect(sliderToBytes(c.slider, scale.sizeLog), String(c.slider)).toBe(c.bytes)
    for (const c of scale.toSlider)
      expect(bytesToSlider(c.bytes, scale.sizeLog), String(c.bytes)).toBe(c.slider)
  })
})
