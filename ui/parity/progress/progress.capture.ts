/**
 * The progress corpus: sequences of job and run samples to version 1's
 * percentage, estimate, phase text and tooltip, as pollSync computes them.
 * Covers removal weighting, the 99 per cent cap while running, the rate
 * measured from the first byte, and a second run banking the first.
 */
import { join } from 'node:path'
import { normalise } from '../fixture/fixture.ts'
import { syntheticLibrary } from '../library/library.ts'
import { UI_ROOT, bootV1 } from '../v1/v1.ts'

export const FIXTURE = join(UI_ROOT, 'src/lib/progress/__fixtures__/progress.v1.json')

const MB = 1 << 20

type Status = {
  readonly state?: string
  readonly cur_bytes?: number
  readonly sent?: number
  readonly removed?: number
  readonly phase?: string
  readonly current?: string
  readonly failed?: number
}
export type Sample = {
  readonly t: number
  readonly run: string | null
  readonly bytes_done?: number
  readonly bytes_removed?: number
  readonly status?: Status
}
export type Scenario = {
  readonly name: string
  readonly start: {
    readonly bytesTotal: number
    readonly removesTotal: number
    readonly onDevice: number
    readonly free: number | null
  }
  readonly samples: readonly Sample[]
}

const start = (bytesTotal: number, removesTotal = 0) => ({
  bytesTotal,
  removesTotal,
  onDevice: 120,
  free: null,
})
const running = (s: Status): Status => ({ state: 'running', ...s })

export const SCENARIOS: readonly Scenario[] = [
  {
    name: 'starting, nothing moved',
    start: start(100 * MB),
    samples: [
      { t: 1000, run: null },
      { t: 2000, run: 'r1', bytes_done: 0, bytes_removed: 0, status: running({ phase: 'scan' }) },
    ],
  },
  {
    name: 'a steady rate from the first byte',
    start: start(100 * MB),
    samples: [
      { t: 0, run: 'r1', bytes_done: 0, bytes_removed: 0, status: running({ phase: 'send' }) },
      {
        t: 1000,
        run: 'r1',
        bytes_done: 10 * MB,
        bytes_removed: 0,
        status: running({ sent: 1, current: 'Galaga' }),
      },
      {
        t: 2000,
        run: 'r1',
        bytes_done: 20 * MB,
        bytes_removed: 0,
        status: running({ sent: 2, current: 'Contra' }),
      },
      {
        t: 4000,
        run: 'r1',
        bytes_done: 40 * MB,
        bytes_removed: 0,
        status: running({ sent: 4, current: 'Journey' }),
      },
      {
        t: 8000,
        run: 'r1',
        bytes_done: 70 * MB,
        bytes_removed: 0,
        status: running({ sent: 7, cur_bytes: 5 * MB, current: 'Lumines' }),
      },
    ],
  },
  {
    name: 'removals weighted at one megabyte each',
    start: start(0, 50),
    samples: [
      {
        t: 0,
        run: 'r1',
        bytes_done: 0,
        bytes_removed: 0,
        status: running({ phase: 'remove', current: 'Patapon' }),
      },
      {
        t: 3000,
        run: 'r1',
        bytes_done: 0,
        bytes_removed: 200 * MB,
        status: running({ phase: 'remove', removed: 10, current: 'Okami' }),
      },
      {
        t: 9000,
        run: 'r1',
        bytes_done: 0,
        bytes_removed: 900 * MB,
        status: running({ phase: 'remove', removed: 50 }),
      },
    ],
  },
  {
    name: 'capped at 99 while running',
    start: start(10 * MB),
    samples: [
      { t: 0, run: 'r1', bytes_done: 0, bytes_removed: 0, status: running({}) },
      { t: 5000, run: 'r1', bytes_done: 10 * MB, bytes_removed: 0, status: running({ sent: 1 }) },
      {
        t: 6000,
        run: 'r1',
        bytes_done: 10 * MB,
        bytes_removed: 0,
        status: running({ sent: 1, cur_bytes: 2 * MB }),
      },
    ],
  },
  {
    name: 'a second run banks the first',
    start: start(60 * MB, 4),
    samples: [
      { t: 0, run: 'r1', bytes_done: 0, bytes_removed: 0, status: running({}) },
      {
        t: 3000,
        run: 'r1',
        bytes_done: 30 * MB,
        bytes_removed: 8 * MB,
        status: running({ sent: 3, removed: 2 }),
      },
      { t: 4000, run: 'r2', bytes_done: 5 * MB, bytes_removed: 0, status: running({ sent: 1 }) },
      {
        t: 7000,
        run: 'r2',
        bytes_done: 25 * MB,
        bytes_removed: 4 * MB,
        status: running({ sent: 2, removed: 2 }),
      },
    ],
  },
  {
    name: 'phase text',
    start: start(100 * MB),
    samples: [
      {
        t: 0,
        run: 'r1',
        bytes_done: 0,
        bytes_removed: 0,
        status: running({ phase: 'remove', current: 'Galaga' }),
      },
      {
        t: 1000,
        run: 'r1',
        bytes_done: 0,
        bytes_removed: 0,
        status: running({ phase: 'send', current: 'Metal Slug' }),
      },
      { t: 2000, run: 'r1', bytes_done: 0, bytes_removed: 0, status: running({ phase: 'verify' }) },
      { t: 3000, run: 'r1', bytes_done: 0, bytes_removed: 0, status: running({}) },
      {
        t: 4000,
        run: 'r1',
        bytes_done: 0,
        bytes_removed: 0,
        status: running({ current: 'Tom & Jerry <Deluxe>' }),
      },
    ],
  },
  {
    name: 'failures in the tooltip',
    start: start(20 * MB),
    samples: [
      { t: 0, run: 'r1', bytes_done: 0, bytes_removed: 0, status: running({}) },
      {
        t: 4000,
        run: 'r1',
        bytes_done: 8 * MB,
        bytes_removed: 0,
        status: running({ sent: 1, failed: 2 }),
      },
    ],
  },
  {
    name: 'bytes in flight count only while running',
    start: start(20 * MB),
    samples: [
      {
        t: 0,
        run: 'r1',
        bytes_done: 4 * MB,
        bytes_removed: 0,
        status: { state: 'paused', cur_bytes: 3 * MB },
      },
      {
        t: 1000,
        run: 'r1',
        bytes_done: 4 * MB,
        bytes_removed: 0,
        status: running({ cur_bytes: 3 * MB }),
      },
    ],
  },
]

const RESET = `(function (s) {
  if (SYNC.timer) clearInterval(SYNC.timer);
  Object.assign(SYNC, { job: 'job-1', device: null, t0: 0, tFirst: 0, timer: null, last: null, curRun: null, curLast: null,
    prev: { bytes: 0, sent: 0, removed: 0, freed: 0 },
    start: { free: s.free, capacity: null, onDevice: s.onDevice, bytesTotal: s.bytesTotal, removesTotal: s.removesTotal, plan: {} } });
  Date.now = () => globalThis.__clock;
})`

export type ProgressCase = { readonly scenario: Scenario; readonly polls: readonly unknown[] }

export async function captureProgress(): Promise<ProgressCase[]> {
  let sample: Sample | undefined
  const v1 = await bootV1({
    library: syntheticLibrary(),
    respond: (path) => {
      if (!sample) throw new Error(`no sample for /api/${path}`)
      if (path.startsWith('job/')) return { state: 'running', run: sample.run }
      if (path.startsWith('run/')) {
        return {
          bytes_done: sample.bytes_done ?? 0,
          bytes_removed: sample.bytes_removed ?? 0,
          status: sample.status ?? {},
        }
      }
      throw new Error(`no answer for /api/${path}`)
    },
  })
  try {
    const cases: ProgressCase[] = []
    for (const scenario of SCENARIOS) {
      v1.evaluate(`${RESET}(${JSON.stringify(scenario.start)})`)
      const polls: unknown[] = []
      for (const s of scenario.samples) {
        sample = s
        v1.evaluate(`globalThis.__clock = ${s.t}`)
        await v1.evaluate<Promise<void>>('pollSync()')
        polls.push(
          v1.evaluate(
            '({ last: SYNC.last, prev: SYNC.prev, curRun: SYNC.curRun, tFirst: SYNC.tFirst })',
          ),
        )
      }
      cases.push({ scenario, polls })
    }
    if (v1.errors.length) throw new Error(`version 1 reported: ${v1.errors.join('; ')}`)
    return normalise(cases) as ProgressCase[]
  } finally {
    v1.close()
  }
}

export const PROGRESS = { name: 'progress', fixture: FIXTURE, capture: captureProgress } as const
