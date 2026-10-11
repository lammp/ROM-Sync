/**
 * Sync progress (F11-S18), version 1's pollSync arithmetic as pure functions.
 *
 * A sync is one job of one or more runs. When the run id changes, the last
 * reading of the finished run is banked, so totals carry across runs. Work
 * is bytes moved plus one megabyte per removal; the percentage is floored
 * and held at 99 until the job itself says it is done. The rate is averaged
 * from the first moment any work moved, not from the start, because an MTP
 * session can sit for minutes before its first byte, and it is not trusted
 * until two seconds of it exist.
 */
import { formatBytes } from '../format/format'

/** One megabyte: the work a removal counts as. */
export const REMOVAL_WORK = 1 << 20
/** How long the rate is measured before an estimate is shown, in milliseconds. */
export const RATE_SETTLE_MS = 2000

export type Totals = {
  readonly bytes: number
  readonly sent: number
  readonly removed: number
  readonly freed: number
}
export const NONE: Totals = { bytes: 0, sent: 0, removed: 0, freed: 0 }

/** What the device held, and what the plan would move, when the sync began. */
export type Start = {
  readonly bytesTotal: number
  readonly removesTotal: number
  readonly onDevice: number
  readonly free: number | null
}

export type RunStatus = {
  readonly state?: string
  readonly phase?: string
  readonly current?: string
  readonly cur_bytes?: number
  readonly sent?: number
  readonly removed?: number
  readonly failed?: number
}

/** One poll: the job's current run, and that run's brief report when there is one. */
export type Sample = {
  readonly run: string | null
  readonly bytes_done?: number
  readonly bytes_removed?: number
  readonly status?: RunStatus
}

export type Tracker = {
  /** Totals banked from finished runs. */
  readonly prev: Totals
  readonly run: string | null
  readonly last: Totals | null
  /** When work first moved, in milliseconds; 0 until it has. */
  readonly firstAt: number
}

export const FRESH: Tracker = { prev: NONE, run: null, last: null, firstAt: 0 }

export type Reading = {
  readonly pct: number
  readonly eta: number | null
  readonly phase: string
  readonly tip: string
  /** Everything moved so far, banked runs included. */
  readonly totals: Totals
  /** Games on the device now: the start, plus sent, less removed. */
  readonly onDevice: number
  /** Free space now, when it was known at the start. */
  readonly free: number | null
  readonly failed: number
}

function add(a: Totals, b: Totals): Totals {
  return {
    bytes: a.bytes + b.bytes,
    sent: a.sent + b.sent,
    removed: a.removed + b.removed,
    freed: a.freed + b.freed,
  }
}

/** The run's report, which exists only once the job names a run. */
function statusOf(sample: Sample): RunStatus {
  return sample.run ? (sample.status ?? {}) : {}
}

/** The current run's totals: bytes done, plus the file in flight while it runs. */
export function current(sample: Sample): Totals {
  const st = statusOf(sample)
  const done = sample.run ? (sample.bytes_done ?? 0) : 0
  return {
    bytes: done + (st.state === 'running' ? st.cur_bytes || 0 : 0),
    sent: st.sent || 0,
    removed: st.removed || 0,
    freed: sample.run ? (sample.bytes_removed ?? 0) : 0,
  }
}

function phaseOf(st: RunStatus): string {
  if (st.phase === 'remove') return `removing ${st.current || ''}`
  if (st.current) return `sending ${st.current || ''}`
  return st.phase || 'starting'
}

/** Takes one poll; returns the new tracker and what to show. */
export function advance(
  t: Tracker,
  start: Start,
  sample: Sample,
  now: number,
): { tracker: Tracker; reading: Reading } {
  let { prev, run } = t
  if (sample.run && sample.run !== run) {
    if (run && t.last) prev = add(prev, t.last)
    run = sample.run
  }
  const cur = current(sample)
  const totals = add(prev, cur)
  const work = totals.bytes + totals.removed * REMOVAL_WORK
  const total = Math.max(1, start.bytesTotal + start.removesTotal * REMOVAL_WORK)
  const pct = Math.min(99, Math.floor((work / total) * 100))
  const firstAt = work > 0 && !t.firstAt ? now : t.firstAt
  const rate = firstAt && now - firstAt > RATE_SETTLE_MS ? work / ((now - firstAt) / 1000) : 0
  const eta = rate > 0 ? (total - work) / rate : null
  const st = statusOf(sample)
  const failed = st.failed || 0
  const tip =
    `${formatBytes(totals.bytes)} of ${formatBytes(start.bytesTotal)} moved · sent ${totals.sent}` +
    ` · removed ${totals.removed} · failed ${failed}${rate ? ` · ${formatBytes(rate)}/s` : ''}`
  return {
    tracker: { prev, run, last: cur, firstAt },
    reading: {
      pct,
      eta,
      phase: phaseOf(st),
      tip,
      totals,
      onDevice: Math.max(0, start.onDevice + totals.sent - totals.removed),
      free: start.free == null ? null : start.free - totals.bytes + totals.freed,
      failed,
    },
  }
}
