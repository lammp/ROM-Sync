import type { CSSProperties, ReactNode } from 'react'
import styles from './CardGrid.module.css'

/** Cards in as many columns as fit, each at least `min` pixels wide. */
export function CardGrid({
  min = 320,
  label,
  children,
}: {
  min?: number
  label: string
  children: ReactNode
}) {
  return (
    <ul
      className={styles.cards}
      aria-label={label}
      style={{ '--card-min': `${min}px` } as CSSProperties}
    >
      {children}
    </ul>
  )
}
