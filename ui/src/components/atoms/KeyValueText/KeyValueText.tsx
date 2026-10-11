import type { ReactNode } from 'react'
import styles from './KeyValueText.module.css'

/** A small muted line that may break anywhere: a file path, a hash. */
export function KeyValueText({ children }: { children: ReactNode }) {
  return <div className={styles.kv}>{children}</div>
}
