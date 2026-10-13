import type { ReactNode } from 'react'
import styles from './LibraryLayout.module.css'

export type LibraryLayoutProps = {
  readonly sidebar: ReactNode
  readonly children: ReactNode
  /** The detail panel, when a game is open. */
  readonly panel?: ReactNode
}

/** The library: filters on the left, the grid in the middle, the detail panel on the right. */
export function LibraryLayout({ sidebar, children, panel }: LibraryLayoutProps) {
  return (
    <div className={styles.library}>
      <aside className={styles.sidebar} aria-label="Filters">
        {sidebar}
      </aside>
      <div className={styles.main}>{children}</div>
      {panel && (
        <aside className={styles.panel} aria-label="Game details">
          {panel}
        </aside>
      )}
    </div>
  )
}
