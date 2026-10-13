import { useId, useRef, type KeyboardEvent, type ReactNode } from 'react'
import styles from './Tabs.module.css'

export type Tab = {
  readonly id: string
  readonly label: string
  /** Something in the tab is edited and not saved. */
  readonly dirty?: boolean
  readonly panel: ReactNode
}

export type TabsProps = {
  /** Names the tab list. */
  readonly label: string
  readonly tabs: readonly Tab[]
  readonly selected: string
  readonly onSelect: (id: string) => void
}

/**
 * Tabs (F11-S48): a tab list and one panel shown at a time. Every panel stays
 * mounted, hidden when not chosen, so what is typed in one survives a visit
 * to another. A tab with unsaved edits carries a dot, said in its name. The
 * arrow keys, Home and End move between tabs; Tab reaches each of them too.
 */
export function Tabs({ label, tabs, selected, onSelect }: TabsProps) {
  const base = useId()
  const list = useRef<HTMLDivElement>(null)
  const go = (index: number) => {
    const tab = tabs[(index + tabs.length) % tabs.length]
    if (!tab) return
    onSelect(tab.id)
    list.current?.querySelector<HTMLButtonElement>(`#${CSS.escape(`${base}-${tab.id}`)}`)?.focus()
  }
  const onKeyDown = (e: KeyboardEvent) => {
    const at = tabs.findIndex((t) => t.id === selected)
    const to =
      e.key === 'ArrowRight'
        ? at + 1
        : e.key === 'ArrowLeft'
          ? at - 1
          : e.key === 'Home'
            ? 0
            : e.key === 'End'
              ? tabs.length - 1
              : null
    if (to === null) return
    e.preventDefault()
    go(to)
  }
  return (
    <div className={styles.tabs}>
      <div
        ref={list}
        role="tablist"
        aria-label={label}
        className={styles.list}
        onKeyDown={onKeyDown}
      >
        {tabs.map((t) => {
          const on = t.id === selected
          return (
            <button
              key={t.id}
              id={`${base}-${t.id}`}
              type="button"
              role="tab"
              aria-selected={on}
              aria-controls={`${base}-${t.id}-panel`}
              aria-label={t.dirty ? `${t.label}, unsaved changes` : undefined}
              className={styles.tab}
              onClick={() => onSelect(t.id)}
            >
              {t.label}
              {t.dirty && <span className={styles.dirty} aria-hidden="true" />}
            </button>
          )
        })}
      </div>
      {tabs.map((t) => (
        <div
          key={t.id}
          id={`${base}-${t.id}-panel`}
          role="tabpanel"
          aria-labelledby={`${base}-${t.id}`}
          hidden={t.id !== selected}
          className={styles.panel}
        >
          {t.panel}
        </div>
      ))}
    </div>
  )
}
