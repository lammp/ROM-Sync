'use client'

import { Toast } from '../../../components/molecules/Toast/Toast'
import { appStore, useAppStore } from '../../../store/store'

const dismiss = (id: number) => appStore.getState().ui.dismiss(id)

/** The store's toasts, in their live region. */
export function Toasts() {
  const toasts = useAppStore((s) => s.ui.toasts)
  return <Toast toasts={toasts} onDismiss={dismiss} />
}
