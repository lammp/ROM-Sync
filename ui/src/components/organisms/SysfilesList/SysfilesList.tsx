import { Dot } from '../../atoms/Dot/Dot'
import { SysfileRow, type Readiness } from '../../molecules/SysfileRow/SysfileRow'
import styles from './SysfilesList.module.css'

export type SysfileSystem = {
  readonly key: string
  readonly label: string
  readonly state: Readiness
  /** Games of this system on the device. */
  readonly count: number
}

/** The list's own entry for files under the staging root that belong to no system. */
export const OTHERS = '*others'

export type SysfilesListProps = {
  readonly systems: readonly SysfileSystem[]
  readonly others: number
  readonly stageRoot: string
  readonly active: string | null
  readonly onSelect: (key: string) => void
}

/**
 * The system files page's left pane (F11-S33): systems with games on the
 * device first, most games first, then the rest under a divider, then the
 * stray files under the staging root.
 */
export function SysfilesList({ systems, others, stageRoot, active, onSelect }: SysfilesListProps) {
  const ordered = [...systems].sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
  const on = ordered.filter((s) => s.count > 0)
  const off = ordered.filter((s) => s.count === 0)
  const row = (s: SysfileSystem) => (
    <li key={s.key}>
      <SysfileRow
        label={s.label}
        state={s.state}
        count={s.count}
        active={s.key === active}
        onSelect={() => onSelect(s.key)}
      />
    </li>
  )
  return (
    <ul className={styles.list}>
      {on.map(row)}
      {off.length > 0 && <li className={styles.divider}>in the store, not on the device</li>}
      {off.map(row)}
      <li className={styles.divider}>{stageRoot}</li>
      <li>
        <button
          type="button"
          className={[styles.others, active === OTHERS && styles.active].filter(Boolean).join(' ')}
          aria-current={active === OTHERS ? 'true' : undefined}
          onClick={() => onSelect(OTHERS)}
        >
          <Dot tone={others ? 'warn' : 'neutral'} />
          <span className={styles.name}>Other files</span>
          <span className={styles.n}>{others ? `${others.toLocaleString()} stray` : 'none'}</span>
        </button>
      </li>
    </ul>
  )
}
