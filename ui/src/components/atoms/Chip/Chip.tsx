import type { ReactNode } from 'react'
import styles from './Chip.module.css'

export type ChipKind =
  'plain' | 'system' | 'franchise' | 'suggested' | 'collection' | 'theme' | 'mode' | 'perspective'

export type ChipProps = {
  readonly kind?: ChipKind
  readonly children: ReactNode
  /** Makes the chip a button: a filter to apply, a tag to open. */
  readonly onClick?: () => void
  /** Adds a separate remove button, named for what it removes. */
  readonly onRemove?: () => void
  /** What the remove button removes, for its name; defaults to the text. */
  readonly name?: string
}

/** A tag, a facet value, a system: a rounded label in its kind's colour. */
export function Chip({ kind = 'plain', children, onClick, onRemove, name }: ChipProps) {
  const classes = [styles.chip, styles[kind]].filter(Boolean).join(' ')
  const label = name ?? (typeof children === 'string' ? children : 'tag')
  return (
    <span className={classes}>
      {onClick ? (
        <button type="button" className={styles.action} onClick={onClick}>
          {children}
        </button>
      ) : (
        children
      )}
      {onRemove && (
        <button
          type="button"
          className={styles.remove}
          aria-label={`Remove ${label}`}
          onClick={onRemove}
        >
          <span aria-hidden="true">×</span>
        </button>
      )}
    </span>
  )
}
