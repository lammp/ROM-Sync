/**
 * The capacity level last seen per device, so the warning is given once, on
 * the first crossing into red or full, and not on every poll.
 */
import type { StateCreator } from 'zustand'

export type Level = 'unknown' | 'green' | 'yellow' | 'red' | 'full'

const ALARM: ReadonlySet<Level> = new Set(['red', 'full'])

export type CapacitySlice = {
  readonly capacity: {
    readonly seen: Readonly<Record<string, Level>>
    /** Records a reading; true when it is a new crossing into red or full. */
    note(device: string, level: Level): boolean
    forget(device: string): void
  }
}

export const capacitySlice: StateCreator<CapacitySlice> = (set, get) => ({
  capacity: {
    seen: {},
    note: (device, level) => {
      const before = get().capacity.seen[device]
      set((s) => ({ capacity: { ...s.capacity, seen: { ...s.capacity.seen, [device]: level } } }))
      return ALARM.has(level) && before !== level
    },
    forget: (device) =>
      set((s) => ({
        capacity: {
          ...s.capacity,
          seen: Object.fromEntries(Object.entries(s.capacity.seen).filter(([d]) => d !== device)),
        },
      })),
  },
})
