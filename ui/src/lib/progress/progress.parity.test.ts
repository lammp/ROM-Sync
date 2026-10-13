/**
 * Version 1's pollSync, replayed over all eight captured scenarios: the
 * percentage, the estimate, the phase, the tooltip, the banked totals, the
 * run in hand and when work first moved, after every poll.
 *
 * Version 1 escaped the phase for innerHTML; React escapes what it renders,
 * so the phase here is plain text and is escaped only to compare.
 */
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { readFixture } from '../../../parity/fixture/fixture.ts'
import { FRESH, advance, type Sample, type Start, type Totals, type Tracker } from './progress'

type Poll = {
  last: { pct: number; eta: number | null; phaseText: string; tip: string }
  prev: Totals
  curRun: string | null
  tFirst: number
}
type Case = {
  scenario: { name: string; start: Start; samples: (Sample & { t: number })[] }
  polls: Poll[]
}

const cases = readFixture(join(import.meta.dirname, '__fixtures__/progress.v1.json'))
  .cases as Case[]

const esc = (s: string) =>
  s.replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] ?? c,
  )

describe('progress parity', () => {
  it('covers all eight scenarios', () => {
    expect(cases).toHaveLength(8)
  })

  it('reads every poll as version 1 did', () => {
    for (const { scenario, polls } of cases) {
      let tracker: Tracker = FRESH
      scenario.samples.forEach((sample, i) => {
        const step = advance(tracker, scenario.start, sample, sample.t)
        tracker = step.tracker
        const r = step.reading
        expect(
          {
            last: { pct: r.pct, eta: r.eta, phaseText: esc(r.phase), tip: r.tip },
            prev: tracker.prev,
            curRun: tracker.run,
            tFirst: tracker.firstAt,
          },
          `${scenario.name}, poll ${i + 1}`,
        ).toEqual(polls[i])
      })
    }
  })
})
