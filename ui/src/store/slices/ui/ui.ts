/**
 * Transient interface state: the toasts on screen, the one open dialog, the
 * twin compare card, and the system chosen on the system files page.
 */
import type { StateCreator } from 'zustand'

export type Tone = 'info' | 'bad'
export type Toast = { readonly id: number; readonly text: string; readonly tone: Tone }

export type UiSlice = {
  readonly ui: {
    readonly toasts: readonly Toast[]
    readonly nextToast: number
    readonly dialog: string | null
    readonly twin: number | null
    readonly system: string | null
    toast(text: string, tone?: Tone): number
    dismiss(id: number): void
    openDialog(name: string): void
    closeDialog(): void
    compare(gameId: number | null): void
    pickSystem(system: string | null): void
  }
}

export const uiSlice: StateCreator<UiSlice> = (set, get) => {
  const patch = (p: Partial<UiSlice['ui']>) => set((s) => ({ ui: { ...s.ui, ...p } }))
  return {
    ui: {
      toasts: [],
      nextToast: 1,
      dialog: null,
      twin: null,
      system: null,
      toast: (text, tone = 'info') => {
        const id = get().ui.nextToast
        set((s) => ({
          ui: { ...s.ui, nextToast: id + 1, toasts: [...s.ui.toasts, { id, text, tone }] },
        }))
        return id
      },
      dismiss: (id) =>
        set((s) => ({ ui: { ...s.ui, toasts: s.ui.toasts.filter((t) => t.id !== id) } })),
      openDialog: (name) => patch({ dialog: name }),
      closeDialog: () => patch({ dialog: null }),
      compare: (twin) => patch({ twin }),
      pickSystem: (system) => patch({ system }),
    },
  }
}
