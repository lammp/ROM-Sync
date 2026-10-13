/**
 * The sync in flight: which job, for which device, what the device held and
 * the plan would move when it began, and the progress tracker each poll
 * advances (lib/progress). The arithmetic is lib/progress's; the store only
 * keeps its state between polls, so leaving a page loses nothing.
 */
import type { StateCreator } from 'zustand'
import {
  FRESH,
  advance,
  type Reading,
  type Sample,
  type Start,
  type Tracker,
} from '../../../lib/progress/progress'

export type Running = {
  readonly job: string
  readonly device: string
  readonly start: Start
  readonly tracker: Tracker
  /** What the last poll read; null until the first. */
  readonly reading: Reading | null
}

export type SyncSlice = {
  readonly sync: {
    readonly running: Running | null
    begin(job: string, device: string, start: Start): void
    /** Advances the tracker by one poll of the job's current run. */
    poll(sample: Sample, now: number): void
    finish(): void
  }
}

export const syncSlice: StateCreator<SyncSlice> = (set) => ({
  sync: {
    running: null,
    begin: (job, device, start) =>
      set((s) => ({
        sync: { ...s.sync, running: { job, device, start, tracker: FRESH, reading: null } },
      })),
    poll: (sample, now) =>
      set((s) => {
        const running = s.sync.running
        if (running === null) return s
        const { tracker, reading } = advance(running.tracker, running.start, sample, now)
        return { sync: { ...s.sync, running: { ...running, tracker, reading } } }
      }),
    finish: () => set((s) => ({ sync: { ...s.sync, running: null } })),
  },
})
