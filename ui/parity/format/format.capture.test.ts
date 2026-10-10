import { describe, expect, test } from 'vitest'
import { readFixture } from '../fixture/fixture.ts'
import { FIXTURE, captureFormat, type FormatCases } from './format.capture.ts'

describe('format capture', () => {
  test('corpus', async () => {
    const { header, cases } = readFixture(FIXTURE)
    expect(header.corpus).toBe('format')
    expect(cases).toEqual(await captureFormat())
    const { fmtB, parseSize, fmtEta } = cases as FormatCases
    expect(fmtB.find((c) => c.in === 1024)?.out).toBe('1.00 KB')
    expect(fmtB.find((c) => c.in === null)?.out).toBe('?')
    expect(parseSize.find((c) => c.in === 'abc')?.out).toBeNull()
    expect(fmtEta.find((c) => c.in === 90)?.out).toBe('2 min')
  })
})
