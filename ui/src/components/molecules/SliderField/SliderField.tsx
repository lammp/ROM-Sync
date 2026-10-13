import { useId } from 'react'
import { Range } from '../../atoms/Range/Range'
import styles from './SliderField.module.css'

export type SliderFieldProps = {
  readonly label: string
  /** The value as typed: the field may hold something the scale cannot show yet. */
  readonly value: string
  readonly onChange: (value: string) => void
  readonly min: number
  readonly max: number
  readonly step: number
  /** Said after the number: " s", "%". */
  readonly unit?: string
  readonly help?: string
  readonly error?: string
}

/** How many decimals a step has: 0.01 has two. */
const decimals = (step: number) => (String(step).split('.')[1] ?? '').length

/**
 * A bounded number as a scale (F11-S51), with its number in a small field to
 * the left for fine tuning. Dragging writes the field; typing moves the
 * scale. The bounds are the registry's, so the scale never offers what the
 * engine would refuse.
 */
export function SliderField({
  label,
  value,
  onChange,
  min,
  max,
  step,
  unit = '',
  help,
  error,
}: SliderFieldProps) {
  const id = useId()
  const n = Number(value)
  const at = value.trim() !== '' && Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : min
  const describedBy =
    [help && `${id}-help`, error && `${id}-error`].filter(Boolean).join(' ') || undefined
  return (
    <span className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <span className={styles.row}>
        <span className={styles.number}>
          <input
            id={id}
            type="text"
            inputMode="decimal"
            className={styles.input}
            value={value}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            onChange={(e) => onChange(e.target.value)}
          />
          {unit && <span className={styles.unit}>{unit.trim()}</span>}
        </span>
        <span className={styles.scale}>
          <Range
            label={`${label}, scale`}
            hideLabel
            min={min}
            max={max}
            step={step}
            value={at}
            valueText={`${at.toFixed(decimals(step))}${unit}`}
            onChange={(v) => onChange(v.toFixed(decimals(step)))}
          />
          <span className={styles.bounds} aria-hidden="true">
            <span>{min}</span>
            <span>{max}</span>
          </span>
        </span>
      </span>
      {help && (
        <span id={`${id}-help`} className={styles.help}>
          {help}
        </span>
      )}
      {error && (
        <span id={`${id}-error`} className={styles.error}>
          {error}
        </span>
      )}
    </span>
  )
}
