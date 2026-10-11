import { describe, expect, test } from 'vitest'
import { readFixture } from '../fixture/fixture.ts'
import { FIXTURE, captureProgress, type ProgressCase } from './progress.capture.ts'

type Poll = {
  last: { pct: number; eta: number | null; phaseText: string; tip: string }
  prev: { bytes: number }
}
const polls = (name: string): Poll[] => {
  const found = (readFixture(FIXTURE).cases as ProgressCase[]).find((c) => c.scenario.name === name)
  if (!found) throw new Error(`no scenario named ${name}`)
  return found.polls as Poll[]
}

describe('progress capture', () => {
  test('corpus', async () => {
    const { header, cases } = readFixture(FIXTURE)
    expect(header.corpus).toBe('progress')
    expect(cases).toEqual(await captureProgress())
  })

  test('capped_at_99_while_running', () => {
    expect(polls('capped at 99 while running').at(-1)?.last.pct).toBe(99)
  })

  test('rate_waits_two_seconds_after_the_first_byte', () => {
    const steady = polls('a steady rate from the first byte')
    expect(steady[2]?.last.eta).toBeNull()
    expect(steady[3]?.last.eta).not.toBeNull()
  })

  test('a_new_run_banks_the_last', () => {
    const banks = polls('a second run banks the first').map((p) => p.prev.bytes)
    expect(banks[0]).toBe(0)
    expect(banks[2]).toBe(30 * (1 << 20))
  })

  test('names_are_escaped', () => {
    expect(polls('phase text').at(-1)?.last.phaseText).toBe(
      'sending Tom &amp; Jerry &lt;Deluxe&gt;',
    )
  })
})
