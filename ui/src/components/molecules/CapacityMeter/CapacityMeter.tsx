import { WORDS, type Reading } from '../../../lib/capacity/capacity'
import { formatBytes } from '../../../lib/format/format'
import styles from './CapacityMeter.module.css'

export type CapacityMeterProps = {
  readonly reading: Reading
  /** While a sync runs: free space now and after, rather than the plan alone. */
  readonly live?: boolean
}

/** The destination's space: used now under used after the sync, a percentage, and a sentence. */
export function CapacityMeter({ reading, live = false }: CapacityMeterProps) {
  const selected = `${formatBytes(reading.selected.bytes)} selected`
  const word = WORDS[reading.level]
  if (reading.level === 'unknown') {
    return (
      <div className={[styles.cap, styles.unknown].join(' ')}>
        <span className={styles.meter} role="img" aria-label="Device space: capacity unknown" />
        <span className={styles.pct} aria-hidden="true">
          –
        </span>
        <span className={styles.cnt}>
          <b>{selected}</b> · {word}
          {reading.connected ? '' : ' (not connected)'}
        </span>
      </div>
    )
  }
  const sentence = live
    ? `${formatBytes(reading.free)} free now → ${formatBytes(reading.freeAfter)} after`
    : reading.level === 'full'
      ? `short by ${formatBytes(reading.shortBy)}`
      : `${formatBytes(reading.freeAfter)} free after sync`
  const tip =
    `after sync: ${reading.pctAfter}% used, ${formatBytes(reading.freeAfter)} free\n` +
    `now: ${formatBytes(reading.capacity - reading.free)} used, ${formatBytes(reading.free)} free (${reading.connected ? 'live' : 'last seen'})\n` +
    `selected: ${reading.selected.n.toLocaleString()} games, ${formatBytes(reading.selected.bytes)}`
  return (
    <div className={[styles.cap, styles[reading.level]].join(' ')} title={tip}>
      <span
        className={styles.meter}
        role="meter"
        aria-label="Device space after sync"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={reading.pctAfter}
        aria-valuetext={`${reading.pctAfter}% used after sync, ${word}`}
      >
        <i className={styles.now} style={{ width: `${reading.pctNow}%` }} />
        <i className={styles.after} style={{ width: `${reading.pctAfter}%` }} />
      </span>
      <span className={styles.pct}>{reading.pctAfter}%</span>
      <span className={styles.cnt}>
        <b>{selected}</b> · <span className={styles.word}>{word}</span> · {sentence}
      </span>
    </div>
  )
}
