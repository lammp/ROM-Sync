import type { CSSProperties, ReactNode } from 'react'
import { useWindowedGrid } from '../../../lib/windowing/windowing'
import styles from './VirtualGameGrid.module.css'

export type VirtualGameGridProps<T> = {
  readonly items: readonly T[]
  readonly itemKey: (item: T) => number | string
  readonly renderItem: (item: T) => ReactNode
  readonly view: 'grid' | 'list'
  /** The tile width in pixels, from the tile slider. */
  readonly tile: number
  /** Changes when the list or its look changes (filter, sort), so the row is measured again. */
  readonly layoutKey: unknown
  /** Names the region: "Games, 1,284 shown". */
  readonly label: string
  readonly empty?: ReactNode
}

/**
 * The library's windowed grid (F11-S26): only the rows in and around the
 * viewport exist, over lib/windowing's hook. 8,000 tiles once cost about a
 * second per filter click and 60,000 nodes; this renders a few dozen.
 */
export function VirtualGameGrid<T>({
  items,
  itemKey,
  renderItem,
  view,
  tile,
  layoutKey,
  label,
  empty,
}: VirtualGameGridProps<T>) {
  const grid = view === 'grid'
  const { scroller, inner, layout } = useWindowedGrid(items.length, grid, tile, layoutKey)
  const style: CSSProperties & Record<'--tile', string> = {
    '--tile': `${tile}px`,
    gridTemplateColumns: layout.template || undefined,
    height: layout.measuring || items.length === 0 ? undefined : layout.height,
    paddingTop: layout.paddingTop,
  }
  return (
    <section
      ref={scroller}
      // Focusable, so the keyboard can scroll it before any tile has focus.
      tabIndex={0}
      className={[styles.grid, !grid && styles.list].filter(Boolean).join(' ')}
      aria-label={label}
    >
      {items.length === 0 ? (
        <p className={styles.empty}>{empty ?? 'nothing matches'}</p>
      ) : (
        <ul ref={inner} className={styles.inner} style={style}>
          {items.slice(layout.start, layout.end).map((item) => (
            <li key={itemKey(item)}>{renderItem(item)}</li>
          ))}
        </ul>
      )}
    </section>
  )
}
