import { useEffect } from 'react'
import { IconButton } from '../../atoms/IconButton/IconButton'
import styles from './Toast.module.css'

export type ToastItem = {
  readonly id: number
  readonly text: string
  readonly tone: 'info' | 'bad'
}

/** How long a toast stays, as version 1 kept them: errors longer. */
export const TOAST_MS = { info: 2500, bad: 6000 } as const

function One({ toast, onDismiss }: { toast: ToastItem; onDismiss: (id: number) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), TOAST_MS[toast.tone])
    return () => clearTimeout(timer)
  }, [toast.id, toast.tone, onDismiss])
  return (
    <div className={[styles.toast, toast.tone === 'bad' && styles.bad].filter(Boolean).join(' ')}>
      {toast.tone === 'bad' && <b className={styles.word}>Problem: </b>}
      <span>{toast.text}</span>
      <IconButton label="Dismiss" onClick={() => onDismiss(toast.id)}>
        ×
      </IconButton>
    </div>
  )
}

/**
 * The toasts, inside a live region that is always present, so every toast is
 * announced when it appears (F11-S36). A problem says so in words as well as
 * colour.
 */
export function Toast({
  toasts,
  onDismiss,
}: {
  toasts: readonly ToastItem[]
  onDismiss: (id: number) => void
}) {
  return (
    <div
      className={styles.region}
      role="status"
      aria-label="Notifications"
      aria-live="polite"
      aria-relevant="additions text"
    >
      {toasts.map((t) => (
        <One key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  )
}
