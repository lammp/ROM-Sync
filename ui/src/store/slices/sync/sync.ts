/**
 * The sync in flight: which job, for which device, and what the device held
 * when it began, so progress and the live on-device count are measured from
 * a fixed start. Finished runs are banked by run id, as version 1's `SYNC`
 * did, so a job of several runs reports one total.
 */
import type { StateCreator } from 'zustand'

export type Totals = { readonly bytes: number; readonly removed: number; readonly copied: number }
export type Start = { readonly free: number; readonly onDevice: number; readonly at: string }

export type Running = {
  readonly job: string
  readonly device: string
  readonly start: Start
  readonly banked: Readonly<Record<string, Totals>>
}

export type SyncSlice = {
  readonly sync: {
    readonly running: Running | null
    begin(job: string, device: string, start: Start): void
    bank(run: string, totals: Totals): void
    finish(): void
  }
}

export const ZERO: Totals = { bytes: 0, removed: 0, copied: 0 }

/** Every banked run's totals added together. */
export function bankedTotal(running: Running | null): Totals {
  return Object.values(running?.banked ?? {}).reduce(
    (a, b) => ({
      bytes: a.bytes + b.bytes,
      removed: a.removed + b.removed,
      copied: a.copied + b.copied,
    }),
    ZERO,
  )
}

export const syncSlice: StateCreator<SyncSlice> = (set) => ({
  sync: {
    running: null,
    begin: (job, device, start) =>
      set((s) => ({ sync: { ...s.sync, running: { job, device, start, banked: {} } } })),
    bank: (run, totals) =>
      set((s) =>
        s.sync.running === null
          ? s
          : {
              sync: {
                ...s.sync,
                running: { ...s.sync.running, banked: { ...s.sync.running.banked, [run]: totals } },
              },
            },
      ),
    finish: () => set((s) => ({ sync: { ...s.sync, running: null } })),
  },
})
