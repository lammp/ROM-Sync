import type { ReactNode } from 'react'
import styles from './SplitPane.module.css'

/** A list beside its detail: 260 px and the rest, one above the other below 900 px. */
export function SplitPane({
  list,
  listLabel,
  children,
}: {
  list: ReactNode
  listLabel: string
  children: ReactNode
}) {
  return (
    <div className={styles.pane}>
      <nav className={styles.list} aria-label={listLabel}>
        {list}
      </nav>
      <section className={styles.detail}>{children}</section>
    </div>
  )
}
