import type { ReactNode } from 'react'
import { formatBytes } from '../../../lib/format/format'
import { GridListToggle, type View } from '../../molecules/GridListToggle/GridListToggle'
import { SortControl, type SortValue } from '../../molecules/SortControl/SortControl'
import { TileSizeControl } from '../../molecules/TileSizeControl/TileSizeControl'
import styles from './LibraryToolbar.module.css'

export type LibraryToolbarProps = {
  readonly shown: { readonly n: number; readonly bytes: number }
  readonly total: number
  readonly sort: string
  readonly onSort: (sort: SortValue) => void
  readonly view: View
  readonly onView: (view: View) => void
  readonly tile: number
  readonly onTile: (px: number) => void
  /** The selection summary and capacity meter, when a device is chosen. */
  readonly selection?: ReactNode
  readonly capacity?: ReactNode
}

/** Above the grid: how many games show, the order, the tile size, the view, and the device's summary. */
export function LibraryToolbar(p: LibraryToolbarProps) {
  return (
    <div className={styles.toolbar} role="toolbar" aria-label="Library">
      <span className={styles.count} role="status">
        {p.shown.n.toLocaleString()} of {p.total.toLocaleString()} · {formatBytes(p.shown.bytes)}
      </span>
      <SortControl value={p.sort} onChange={p.onSort} />
      {p.view === 'grid' && <TileSizeControl value={p.tile} onChange={p.onTile} />}
      <GridListToggle value={p.view} onChange={p.onView} />
      {p.selection && <span className={styles.end}>{p.selection}</span>}
      {p.capacity}
    </div>
  )
}
