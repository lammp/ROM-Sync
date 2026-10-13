import type { ReactNode } from 'react'
import styles from './StatRow.module.css'

/** A label and its figure on one line, as in the settings cards. Use inside a `dl`. */
export function StatRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className={styles.stat}>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}
