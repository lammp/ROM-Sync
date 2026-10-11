/** Version 1's fmtB, parseSize and fmtEta, reproduced on every case F0 captured. */
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { readFixture } from '../../../parity/fixture/fixture.ts'
import { formatBytes, formatEta, parseSize } from './format'

type Case<O> = { in: unknown; out: O }
const cases = readFixture(join(import.meta.dirname, '__fixtures__/format.v1.json')).cases as {
  fmtB: Case<string>[]
  parseSize: Case<number | null>[]
  fmtEta: Case<string>[]
}

describe('format parity', () => {
  it('formatBytes is fmtB', () => {
    expect(cases.fmtB).toHaveLength(21)
    for (const c of cases.fmtB) expect(formatBytes(c.in as number), String(c.in)).toBe(c.out)
  })

  it('parseSize is parseSize', () => {
    expect(cases.parseSize).toHaveLength(24)
    for (const c of cases.parseSize) expect(parseSize(c.in), String(c.in)).toBe(c.out)
  })

  it('formatEta is fmtEta', () => {
    expect(cases.fmtEta).toHaveLength(20)
    for (const c of cases.fmtEta) expect(formatEta(c.in as number), String(c.in)).toBe(c.out)
  })
})
