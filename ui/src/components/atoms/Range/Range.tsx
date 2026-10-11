import { useId } from 'react'
import styles from './Range.module.css'

export type RangeProps = {
  readonly label: string
  readonly min: number
  readonly max: number
  readonly step?: number
  readonly value: number
  readonly onChange: (value: number) => void
  /** What the value means, announced in place of the bare number. */
  readonly valueText?: string
  readonly hideLabel?: boolean
}

/** A single-thumb slider: the rating floor and the tile size. */
export function Range({
  label,
  min,
  max,
  step = 1,
  value,
  onChange,
  valueText,
  hideLabel = false,
}: RangeProps) {
  const id = useId()
  return (
    <span className={styles.field}>
      <label htmlFor={id} className={hideLabel ? styles.hidden : styles.label}>
        {label}
      </label>
      <input
        id={id}
        type="range"
        className={styles.range}
        min={min}
        max={max}
        step={step}
        value={value}
        aria-valuetext={valueText}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </span>
  )
}
