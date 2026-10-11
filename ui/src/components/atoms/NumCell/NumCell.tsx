import type { ReactNode } from 'react'
import styles from './NumCell.module.css'

/** A table cell holding a number: right aligned, in tabular figures. */
export function NumCell({ children, header = false }: { children: ReactNode; header?: boolean }) {
  return header ? (
    <th scope="col" className={styles.num}>
      {children}
    </th>
  ) : (
    <td className={styles.num}>{children}</td>
  )
}
