import { useEffect, useId, useRef, type ReactNode } from 'react'
import styles from './Modal.module.css'

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

export type ModalProps = {
  /** Names the dialog. */
  readonly title: string
  readonly onClose: () => void
  readonly children: ReactNode
  /** The control to focus first; otherwise the first focusable one. */
  readonly initialFocus?: string
}

/**
 * A modal dialog (F11-S25): the dialog role named by its title, focus moved
 * in on open, kept inside while open, given back on close, and Escape to
 * close. Version 1 also closed on a click outside; that is dropped, because
 * a pointer-only dismissal has no control of its own (F11-S10), and Escape
 * and each dialog's Cancel do the same. It replaces version 1's native confirm and
 * prompt, which SPEC section 10 forbids.
 */
export function Modal({ title, onClose, children, initialFocus }: ModalProps) {
  const titleId = useId()
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const before = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const root = box.current
    const first =
      (initialFocus ? root?.querySelector<HTMLElement>(initialFocus) : null) ??
      root?.querySelector<HTMLElement>(FOCUSABLE) ??
      root
    first?.focus()
    return () => {
      if (before?.isConnected) before.focus()
    }
  }, [initialFocus])

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.stopPropagation()
      onClose()
      return
    }
    if (e.key !== 'Tab' || !box.current) return
    const all = [...box.current.querySelectorAll<HTMLElement>(FOCUSABLE)]
    if (all.length === 0) {
      e.preventDefault()
      return
    }
    const first = all[0]
    const last = all[all.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last?.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first?.focus()
    }
  }

  return (
    <div className={styles.backdrop}>
      <div
        ref={box}
        className={styles.box}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onKeyDown={onKeyDown}
      >
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        {children}
      </div>
    </div>
  )
}
