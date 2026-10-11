import { describe, expect, it } from 'vitest'
import { formatBytes, formatEta, parseSize } from './format'

describe('formatBytes', () => {
  it('keeps bare bytes whole and scales by 1024', () => {
    expect([0, 512, 1024, 1536, 10240].map(formatBytes)).toEqual([
      '0 B',
      '512 B',
      '1.00 KB',
      '1.50 KB',
      '10.0 KB',
    ])
  })

  it('stops at terabytes and keeps the sign', () => {
    expect(formatBytes(2 ** 50)).toBe('1024.0 TB')
    expect(formatBytes(-3 * 2 ** 30)).toBe('-3.00 GB')
  })

  it('says it does not know', () => {
    expect([null, undefined].map(formatBytes)).toEqual(['?', '?'])
  })
})

describe('parseSize', () => {
  it('reads binary units with or without the b, and spaces', () => {
    expect(['4k', '4 KB', '1.5 m', '2G', '1 tb', '99'].map(parseSize)).toEqual([
      4096,
      4096,
      1572864,
      2 ** 31,
      2 ** 40,
      99,
    ])
  })

  it('refuses what is not a size', () => {
    expect(['', 'big', '-1k', '1e6', '3 pb', null].map(parseSize)).toEqual([
      null,
      null,
      null,
      null,
      null,
      null,
    ])
  })
})

describe('formatEta', () => {
  it('rounds into seconds, minutes and hours', () => {
    expect([0.4, 42, 61, 3599, 7200].map(formatEta)).toEqual([
      '1 s',
      '42 s',
      '1 min',
      '60 min',
      '2.0 h',
    ])
  })

  it('waits with an ellipsis until it can know', () => {
    expect([null, undefined, NaN, Infinity].map(formatEta)).toEqual(['…', '…', '…', '…'])
  })
})
