import type { ReactNode } from 'react'
import styles from './Muted.module.css'

/** Secondary text: counts, labels, captions. */
export function Muted({ children }: { children: ReactNode }) {
  return <span className={styles.muted}>{children}</span>
}
