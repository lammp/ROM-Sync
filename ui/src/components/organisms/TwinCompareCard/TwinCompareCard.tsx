import { useEffect, useId, useRef, type CSSProperties } from 'react'
import { IconButton } from '../../atoms/IconButton/IconButton'
import { TwinRow, type TwinRowProps } from '../../molecules/TwinRow/TwinRow'
import styles from './TwinCompareCard.module.css'

export type TwinCompareCardProps = {
  /** IGDB's canonical name the versions met on, or null when they met on the file name. */
  readonly matchedOn: string | null
  /** The card's own game first, then each other version. */
  readonly rows: readonly (TwinRowProps & { readonly id: number })[]
  readonly onClose: () => void
  /** Where to draw it, beside the tile it belongs to. */
  readonly anchor?: { readonly top: number; readonly left: number }
}

/**
 * The versions of the selected game on other systems (F11-S30). It belongs
 * to the selected tile only, opens from that tile's twin mark by pointer or
 * keyboard, takes focus, and closes on Escape or its close button. Switch
 * and Select are buttons, so neither needs a pointer.
 */
export function TwinCompareCard({ matchedOn, rows, onClose, anchor }: TwinCompareCardProps) {
  const head = useId()
  const card = useRef<HTMLDivElement>(null)
  useEffect(() => {
    card.current?.focus()
  }, [])
  const others = rows.length - 1
  const position: CSSProperties | undefined = anchor
    ? { top: anchor.top, left: anchor.left }
    : undefined
  return (
    <div
      ref={card}
      className={styles.card}
      style={position}
      role="dialog"
      aria-labelledby={head}
      tabIndex={-1}
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          e.stopPropagation()
          onClose()
        }
      }}
    >
      <div className={styles.top}>
        <h2 id={head} className={styles.head}>
          Same game on {others} other system{others === 1 ? '' : 's'}
        </h2>
        <IconButton label="Close comparison" onClick={onClose}>
          ×
        </IconButton>
      </div>
      {matchedOn ? (
        <p className={styles.key}>matched on IGDB&apos;s name: “{matchedOn}”</p>
      ) : (
        <p className={[styles.key, styles.warn].join(' ')}>
          no IGDB match: matched on the file name, so check these really are the same game
        </p>
      )}
      {rows.map(({ id, ...row }) => (
        <TwinRow key={id} {...row} />
      ))}
    </div>
  )
}
