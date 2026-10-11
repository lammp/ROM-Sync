import { describe, expect, it } from 'vitest'
import {
  FRESH,
  REMOVAL_WORK,
  advance,
  current,
  type Sample,
  type Start,
  type Tracker,
} from './progress'

const MB = 1 << 20
const start: Start = { bytesTotal: 100 * MB, removesTotal: 10, onDevice: 50, free: 1000 * MB }
const running = (over: Partial<Sample> = {}, status: Sample['status'] = {}): Sample => ({
  run: 'r1',
  bytes_done: 0,
  bytes_removed: 0,
  status: { state: 'running', ...status },
  ...over,
})

function replay(samples: [number, Sample][]) {
  let t: Tracker = FRESH
  return samples.map(([now, s]) => {
    const step = advance(t, start, s, now)
    t = step.tracker
    return step.reading
  })
}

describe('progress', () => {
  it('counts a removal as a megabyte of work', () => {
    const [r] = replay([[0, running({}, { removed: 5 })]])
    expect(r?.pct).toBe(Math.floor(((5 * REMOVAL_WORK) / (100 * MB + 10 * REMOVAL_WORK)) * 100))
  })

  it('holds at 99 while the job runs, however much has moved', () => {
    const [r] = replay([[0, running({ bytes_done: 500 * MB }, { removed: 10 })]])
    expect(r?.pct).toBe(99)
  })

  it('counts the file in flight only while the run is running', () => {
    expect(current(running({ bytes_done: MB }, { cur_bytes: 2 * MB })).bytes).toBe(3 * MB)
    expect(
      current(running({ bytes_done: MB, status: { state: 'done', cur_bytes: 2 * MB } })).bytes,
    ).toBe(MB)
  })

  it('ignores a report until the job names a run', () => {
    expect(current({ run: null, bytes_done: 9, status: { sent: 3 } })).toEqual({
      bytes: 0,
      sent: 0,
      removed: 0,
      freed: 0,
    })
  })

  it('measures the rate from the first work, and waits two seconds to estimate', () => {
    const rs = replay([
      [0, running()],
      [60_000, running({ bytes_done: 10 * MB })],
      [61_000, running({ bytes_done: 20 * MB })],
      [64_000, running({ bytes_done: 50 * MB })],
    ])
    expect(rs.map((r) => r.eta === null)).toEqual([true, true, true, false])
    const rate = (50 * MB) / 4
    expect(rs[3]?.eta).toBeCloseTo((100 * MB + 10 * REMOVAL_WORK - 50 * MB) / rate)
  })

  it('banks a finished run when the next one starts', () => {
    const rs = replay([
      [0, running({ bytes_done: 30 * MB, bytes_removed: 8 * MB }, { sent: 3, removed: 2 })],
      [1, running({ run: 'r2', bytes_done: 5 * MB }, { sent: 1 })],
    ])
    expect(rs[1]?.totals).toEqual({ bytes: 35 * MB, sent: 4, removed: 2, freed: 8 * MB })
  })

  it('derives the live on-device count and free space', () => {
    const [r] = replay([
      [0, running({ bytes_done: 10 * MB, bytes_removed: 4 * MB }, { sent: 7, removed: 2 })],
    ])
    expect([r?.onDevice, r?.free]).toEqual([55, 1000 * MB - 10 * MB + 4 * MB])
    const unknown = advance(FRESH, { ...start, free: null }, running(), 0).reading
    expect(unknown.free).toBeNull()
  })

  it('says what it is doing', () => {
    const phases = [
      running({}, { phase: 'remove', current: 'snes/a.sfc' }),
      running({}, { current: 'snes/b.sfc' }),
      running({}, { phase: 'scan' }),
      { run: null },
    ].map((s) => advance(FRESH, start, s, 0).reading.phase)
    expect(phases).toEqual(['removing snes/a.sfc', 'sending snes/b.sfc', 'scan', 'starting'])
  })
})
