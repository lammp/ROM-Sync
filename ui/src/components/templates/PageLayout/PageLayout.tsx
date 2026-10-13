import type { ReactNode } from 'react'
import styles from './PageLayout.module.css'

/**
 * A page with its heading and, beside it, its actions; the page itself
 * scrolls. The actions sit outside the heading, so the heading's name is the
 * page's name alone.
 */
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
      <header className={styles.head}>
        <h1 className={styles.heading}>{heading}</h1>
        {actions && <div className={styles.actions}>{actions}</div>}
      </header>
      {children}
    </div>
  )
}
