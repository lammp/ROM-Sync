/**
 * The device the library is curated for. Which games are selected is the
 * engine's (a query); the store holds only which device is in view.
 */
import type { StateCreator } from 'zustand'

export type SelectionSlice = {
  readonly selection: {
    readonly device: string | null
    choose(device: string | null): void
  }
}

export const selectionSlice: StateCreator<SelectionSlice> = (set) => ({
  selection: {
    device: null,
    choose: (device) => set((s) => ({ selection: { ...s.selection, device: device || null } })),
  },
})
