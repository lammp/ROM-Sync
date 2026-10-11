import type { ReactNode } from 'react'
import styles from './PageLayout.module.css'

/** A page with its heading; the page itself scrolls. */
export function PageLayout({
  heading,
  actions,
  children,
}: {
  heading: ReactNode
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>
        {heading}
        {actions && <span className={styles.actions}>{actions}</span>}
      </h1>
      {children}
    </div>
  )
}
