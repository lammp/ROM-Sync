import type { ReactNode } from 'react'
import styles from './SplitPane.module.css'

/** A list beside its detail where the space allows, one above the other where it does not. */
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
    <div className={styles.frame}>
      <div className={styles.pane}>
        <nav className={styles.list} aria-label={listLabel}>
          {list}
        </nav>
        <section className={styles.detail}>{children}</section>
      </div>
    </div>
  )
}
