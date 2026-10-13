import { describe, expect, it } from 'vitest'
import { DEFAULT_BOUNDS, SLIDER_MAX, bytesToSlider, logBounds, sliderToBytes } from './scale'

describe('scale', () => {
  it('treats both ends of the slider as no limit', () => {
    expect([0, -5, SLIDER_MAX, 2000].map((v) => sliderToBytes(v, DEFAULT_BOUNDS))).toEqual([
      null,
      null,
      null,
      null,
    ])
  })

  it('round-trips a position through bytes', () => {
    const b = logBounds([2048, 5_000_000_000])
    for (const v of [1, 250, 500, 999]) {
      const bytes = sliderToBytes(v, b)
      expect(bytes).not.toBeNull()
      expect(bytesToSlider(bytes, b)).toBe(v)
    }
  })

  it('bounds the scale by the library, from at least 1 KB to 5 per cent past the largest', () => {
    const b = logBounds([0, 10, 4096, 1_000_000])
    expect(b.min).toBeCloseTo(Math.log(1024))
    expect(b.max).toBeCloseTo(Math.log(1_050_000))
    expect(logBounds([])).toEqual(DEFAULT_BOUNDS)
  })

  it('places a size under 1 KB as 1 KB, and none as none', () => {
    expect(bytesToSlider(1, DEFAULT_BOUNDS)).toBe(0)
    expect(bytesToSlider(null, DEFAULT_BOUNDS)).toBeNull()
  })
})
