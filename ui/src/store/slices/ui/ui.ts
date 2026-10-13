/**
 * Interface state: the toasts on screen, the one open dialog, the twin
 * compare card, the system chosen on the system files page, and the
 * notifications (F11-S47), which are kept in the browser across reloads.
 */
import type { StateCreator } from 'zustand'
import { KEPT, type Notice } from '../../../lib/notices/notices'

export type Tone = 'info' | 'bad'
export type Toast = { readonly id: number; readonly text: string; readonly tone: Tone }
export type Kept = Notice & { readonly read: boolean }

/** How many cleared ids are remembered, so a cleared event is not raised again. */
export const CLEARED_KEPT = 500

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
    /** Newest first. */
    readonly notices: readonly Kept[]
    /** Ids the person cleared: never raised again. */
    readonly cleared: readonly string[]
    /** Adds a notification, unread; false when it is already there or was cleared. */
    notify(notice: Notice): boolean
    /** Takes a notification away without counting it cleared: a setup step now done. */
    retract(id: string): void
    clearNotice(id: string): void
    clearNotices(): void
    readNotices(): void
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
      notices: [],
      cleared: [],
      notify: (notice) => {
        const { notices, cleared } = get().ui
        if (cleared.includes(notice.id) || notices.some((n) => n.id === notice.id)) return false
        patch({ notices: [{ ...notice, read: false }, ...notices].slice(0, KEPT) })
        return true
      },
      retract: (id) => patch({ notices: get().ui.notices.filter((n) => n.id !== id) }),
      clearNotice: (id) => {
        const { notices, cleared } = get().ui
        patch({
          notices: notices.filter((n) => n.id !== id),
          cleared: [id, ...cleared.filter((c) => c !== id)].slice(0, CLEARED_KEPT),
        })
      },
      clearNotices: () => {
        const { notices, cleared } = get().ui
        patch({
          notices: [],
          cleared: [...notices.map((n) => n.id), ...cleared].slice(0, CLEARED_KEPT),
        })
      },
      readNotices: () =>
        patch({ notices: get().ui.notices.map((n) => (n.read ? n : { ...n, read: true })) }),
    },
  }
}
