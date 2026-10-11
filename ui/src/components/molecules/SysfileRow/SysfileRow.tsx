import { Dot, type DotTone } from '../../atoms/Dot/Dot'
import styles from './SysfileRow.module.css'

export type Readiness = 'unknown' | 'none' | 'unseen' | 'missing' | 'optional' | 'ready'

/** Each readiness state's colour and word; the word is always drawn. */
export const READINESS: Readonly<Record<Readiness, readonly [DotTone, string]>> = {
  ready: ['ok', 'ready'],
  missing: ['bad', 'missing'],
  optional: ['warn', 'optional'],
  none: ['neutral', 'nothing needed'],
  unseen: ['neutral', 'not seen over USB'],
  unknown: ['neutral', 'not scanned'],
}

export type SysfileRowProps = {
  readonly label: string
  readonly state: Readiness
  /** Games of this system on the device; none mutes the row. */
  readonly count: number
  readonly active: boolean
  readonly onSelect: () => void
}

/** One system in the system-files list: its readiness in a dot and a word. */
export function SysfileRow({ label, state, count, active, onSelect }: SysfileRowProps) {
  const [tone, word] = READINESS[state]
  return (
    <button
      type="button"
      aria-current={active ? 'true' : undefined}
      className={[styles.row, active && styles.active, count === 0 && styles.dim]
        .filter(Boolean)
        .join(' ')}
      onClick={onSelect}
    >
      <Dot tone={tone} />
      <span className={styles.name}>{label}</span>
      <span className={styles.word}>{word}</span>
      <span className={styles.n}>{count ? `${count.toLocaleString()} games` : 'no games'}</span>
    </button>
  )
}
