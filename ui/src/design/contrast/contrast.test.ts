import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { COLOUR } from '../tokens/tokens'
import {
  PAIRS,
  SURFACES,
  TARGET,
  composite,
  failures,
  measure,
  parse,
  ratio,
  type Pair,
} from './contrast'

type Measured = { label: string; fg: string; bg: string; ratio: number }
const measured = (
  JSON.parse(
    readFileSync(join(import.meta.dirname, '../tokens/__fixtures__/palette.v1.json'), 'utf8'),
  ) as { cases: { pairs: Measured[] } }
).cases.pairs

describe('contrast', () => {
  it('agrees with the instrument of record on all 31 measured pairs', () => {
    for (const p of measured) expect(ratio(p.fg, p.bg), p.label).toBeCloseTo(p.ratio, 2)
  })

  it('spans 1 to 21 and is symmetric', () => {
    expect(ratio('#ffffff', '#000000')).toBeCloseTo(21, 6)
    expect(ratio('#123456', '#123456')).toBe(1)
    expect(ratio('#4f8cff', '#1a1c22')).toBeCloseTo(ratio('#1a1c22', '#4f8cff'), 10)
  })

  it('composites a translucent colour over its surface', () => {
    expect(composite(parse('rgba(255, 255, 255, 0.5)'), parse('#000000'))).toEqual({
      r: 127.5,
      g: 127.5,
      b: 127.5,
      a: 1,
    })
    expect(ratio('rgba(0, 0, 0, 0)', '#1a1c22')).toBe(1)
  })

  it('refuses what is not a colour, and a translucent surface', () => {
    expect(() => parse('red')).toThrow('not a colour')
    expect(() => ratio('#ffffff', 'rgba(0, 0, 0, 0.5)')).toThrow('opaque')
  })

  it('aa_all_pairs', () => {
    expect(failures()).toEqual([])
    for (const p of PAIRS) expect(measure(p), p.label).toBeGreaterThanOrEqual(TARGET[p.kind])
  })

  it('reports a pair that falls short', () => {
    const weak: Pair = { label: 'old line', fg: '--divider', bg: '--bg3', kind: 'non-text' }
    const [failed] = failures([weak])
    expect(failed?.label).toBe('old line')
    expect(failed?.ratio).toBeCloseTo(1.18, 2)
  })

  it('focus_ring_on_every_surface', () => {
    for (const bg of SURFACES) {
      expect(ratio(COLOUR['--focus'], COLOUR[bg]), bg).toBeGreaterThanOrEqual(TARGET['non-text'])
      expect(PAIRS.some((p) => p.fg === '--focus' && p.bg === bg)).toBe(true)
    }
  })

  it('measures every text colour the set declares on at least one surface', () => {
    const drawn = new Set(PAIRS.filter((p) => p.kind === 'text').map((p) => p.fg))
    for (const fg of [
      '--fg',
      '--fg-soft',
      '--muted',
      '--on-accent',
      '--on-ok',
      '--on-warn',
    ] as const)
      expect(drawn.has(fg), fg).toBe(true)
  })
})
