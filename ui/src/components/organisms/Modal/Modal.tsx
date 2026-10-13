import { useEffect, useId, useRef, type ReactNode } from 'react'
import { IconButton } from '../../atoms/IconButton/IconButton'
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
 * in on open, kept inside while open, and given back on close. It closes
 * three ways, every one of them always there: its close button, Escape, and
 * a click on the dimmed page around it. A dialog never leaves the person
 * without a visible way out. It replaces version 1's native confirm and
 * prompt, which SPEC section 10 forbids.
 *
 * The close button comes after the content, so focus opens on the content
 * and the button is drawn in the corner.
 */
export function Modal({ title, onClose, children, initialFocus }: ModalProps) {
  const titleId = useId()
  const box = useRef<HTMLDivElement>(null)
  const backdrop = useRef<HTMLDivElement>(null)

  // A press on the dimmed page around the dialog closes it, as the close button
  // and Escape do; a press that lands inside the dialog does not. It is a native
  // listener: the backdrop is not a control, and the keyboard has its own ways out.
  useEffect(() => {
    const around = backdrop.current
    if (!around) return
    const press = (e: MouseEvent) => {
      if (e.target === around) onClose()
    }
    around.addEventListener('mousedown', press)
    return () => around.removeEventListener('mousedown', press)
  }, [onClose])

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
    <div ref={backdrop} className={styles.backdrop}>
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
        <span className={styles.close}>
          <IconButton label="Close" onClick={onClose}>
            ×
          </IconButton>
        </span>
      </div>
    </div>
  )
}
