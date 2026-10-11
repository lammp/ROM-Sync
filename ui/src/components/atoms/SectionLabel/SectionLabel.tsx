import type { ReactNode } from 'react'
import styles from './SectionLabel.module.css'

/** A small capitalised label over a group in a list: "Needs files", "Ready". */
export function SectionLabel({ children }: { children: ReactNode }) {
  return <div className={styles.label}>{children}</div>
}
