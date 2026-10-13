import { useId } from 'react'
import styles from './Select.module.css'

export type Option = { readonly value: string; readonly label: string }

export type SelectProps = {
  readonly label: string
  readonly options: readonly Option[]
  readonly value: string
  readonly onChange: (value: string) => void
  /** The pill-shaped picker version 1 drew for versions. */
  readonly variant?: 'default' | 'chip'
  readonly hideLabel?: boolean
  readonly disabled?: boolean
}

/** A native select, always with a programmatically associated label. */
export function Select({
  label,
  options,
  value,
  onChange,
  variant = 'default',
  hideLabel = false,
  disabled,
}: SelectProps) {
  const id = useId()
  return (
    <span className={styles.field}>
      <label htmlFor={id} className={hideLabel ? styles.hidden : styles.label}>
        {label}
      </label>
      <select
        id={id}
        className={[styles.select, variant === 'chip' && styles.chip].filter(Boolean).join(' ')}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </span>
  )
}
