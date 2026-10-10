import { describe, expect, test } from 'vitest'
import { readFixture } from '../fixture/fixture.ts'
import { FIXTURE, captureTokens, parseReport, type TokenCases } from './tokens.capture.ts'

describe('tokens capture', () => {
  test('as_is_snapshot', async () => {
    const { header, cases } = readFixture(FIXTURE)
    expect(header.corpus).toBe('tokens')
    expect(cases).toEqual(await captureTokens())
    const { pairs, tokens } = cases as TokenCases
    expect(pairs).toHaveLength(31)
    expect(pairs.some((p) => p.verdict === 'FAIL')).toBe(true)
    expect(Object.keys(tokens).length).toBeGreaterThan(0)
  })

  test('reads_the_oracle_report', () => {
    const report = [
      'x.css: 2 declared tokens',
      '',
      'declared tokens',
      '  --fg                         #e6e6e6',
      '  --bg                         #0f1115',
      '',
      'pair                               fg        bg         ratio  need  verdict  correction',
      '-'.repeat(100),
      'body text on page                  #e6e6e6   #0f1115    15.32   4.5  PASS     ',
      'muted text on raised               #6b7280   #1f2430     3.01   4.5  FAIL     #8a919c',
      '-'.repeat(100),
      '1 failing pair(s)',
    ].join('\n')
    expect(parseReport(report)).toEqual({
      tokens: { '--fg': '#e6e6e6', '--bg': '#0f1115' },
      pairs: [
        {
          label: 'body text on page',
          fg: '#e6e6e6',
          bg: '#0f1115',
          ratio: 15.32,
          target: 4.5,
          verdict: 'PASS',
          correction: '',
        },
        {
          label: 'muted text on raised',
          fg: '#6b7280',
          bg: '#1f2430',
          ratio: 3.01,
          target: 4.5,
          verdict: 'FAIL',
          correction: '#8a919c',
        },
      ],
    })
  })
})
