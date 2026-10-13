/**
 * The destination's capacity, as the meter shows it (F11-S21).
 *
 * Read in the interface from the device's capacity and free space and the
 * plan's byte totals, with the thresholds taken from the engine's settings
 * (`capacity.warn_fraction`, `capacity.alarm_fraction`,
 * `plan.free_space_margin`), never from constants in the page. "Full" is the
 * engine's own fit verdict, which it takes at the plan's peak: a sync that
 * sends before it removes can end inside the space and still run out on the
 * way, which version 1's meter, looking only at the end, missed.
 */

export type Level = 'unknown' | 'green' | 'yellow' | 'red' | 'full'

/** The settings the meter reads. */
export type Thresholds = {
  readonly warnFraction: number
  readonly alarmFraction: number
  readonly margin: number
}

export type PlanBytes = {
  readonly add: number
  readonly drop: number
  readonly net: number
  readonly peak: number
  readonly fits: boolean | null
}

export type CapacityInput = {
  readonly capacity: number | null
  readonly free: number | null
  readonly connected: boolean
  readonly selected: { readonly n: number; readonly bytes: number }
  readonly plan: PlanBytes | null
}

export type Known = {
  readonly level: Exclude<Level, 'unknown'>
  readonly capacity: number
  readonly free: number
  /** Percent used now and after the sync, each held to 0 to 100. */
  readonly pctNow: number
  readonly pctAfter: number
  readonly freeAfter: number
  /** How much more space the sync needs than there is, when it does not fit. */
  readonly shortBy: number
}

export type Reading = {
  readonly connected: boolean
  readonly selected: CapacityInput['selected']
} & ({ readonly level: 'unknown' } | Known)

/** The word each level carries beside its colour. */
export const WORDS: Readonly<Record<Level, string>> = {
  unknown: 'capacity unknown',
  green: 'fits',
  yellow: 'getting full',
  red: 'nearly full',
  full: 'will not fit',
}

const clamp = (n: number) => Math.min(100, Math.max(0, Math.round(n)))

export function read(input: CapacityInput, t: Thresholds): Reading {
  const { capacity, free, connected, selected, plan } = input
  if (!capacity || free == null) return { level: 'unknown', connected, selected }
  const net = plan?.net ?? 0
  const usedAfter = capacity - free + net
  const fraction = usedAfter / capacity
  const level: Known['level'] =
    plan?.fits === false
      ? 'full'
      : fraction >= t.alarmFraction
        ? 'red'
        : fraction >= t.warnFraction
          ? 'yellow'
          : 'green'
  return {
    level,
    connected,
    selected,
    capacity,
    free,
    pctNow: clamp(((capacity - free) / capacity) * 100),
    pctAfter: clamp(fraction * 100),
    freeAfter: free - net,
    shortBy: plan?.fits === false ? Math.max(0, (plan.peak ?? 0) + t.margin - free) : 0,
  }
}
