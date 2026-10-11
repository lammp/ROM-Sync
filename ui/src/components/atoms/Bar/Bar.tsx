import styles from './Bar.module.css'

export type BarProps = {
  /** The share filled, from 0 to 1; values outside are held to the ends. */
  readonly value: number
  readonly label: string
  /** What the value means, announced in place of a bare percentage. */
  readonly valueText?: string
  readonly dim?: boolean
}

/** A single-fill meter: a device's used space, a system's share. */
export function Bar({ value, label, valueText, dim = false }: BarProps) {
  const share = Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0))
  const percent = Math.round(share * 100)
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      aria-valuetext={valueText ?? `${percent}%`}
      className={[styles.bar, dim && styles.dim].filter(Boolean).join(' ')}
    >
      <i className={styles.fill} style={{ width: `${share * 100}%` }} />
    </div>
  )
}
