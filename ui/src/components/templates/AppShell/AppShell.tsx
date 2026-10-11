import type { ReactNode } from 'react'
import styles from './AppShell.module.css'

export type AppShellProps = {
  readonly header: ReactNode
  readonly children: ReactNode
  /** Where dialogs mount, above everything. */
  readonly modals?: ReactNode
  /** Where toasts mount; the live region lives inside it. */
  readonly toasts?: ReactNode
}

/** The page: a header, the main region below it filling the window, and the two hosts. */
export function AppShell({ header, children, modals, toasts }: AppShellProps) {
  return (
    <div className={styles.shell}>
      <a className={styles.skip} href="#main">
        Skip to content
      </a>
      <header className={styles.header}>{header}</header>
      <main id="main" className={styles.main} tabIndex={-1}>
        {children}
      </main>
      {modals}
      {toasts}
    </div>
  )
}
