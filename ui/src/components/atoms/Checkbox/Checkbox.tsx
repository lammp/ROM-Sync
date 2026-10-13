import type { ReactNode } from 'react'
import styles from './Checkbox.module.css'

export type CheckboxProps = {
  /** Drawn beside the box and naming it; a checkbox without one does not exist. */
  readonly label: ReactNode
  readonly checked: boolean
  readonly onChange: (checked: boolean) => void
  readonly disabled?: boolean
}

/** A checkbox wrapped in its label, so the label names it and is clickable. */
export function Checkbox({ label, checked, onChange, disabled }: CheckboxProps) {
  return (
    <label className={styles.row}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>{label}</span>
    </label>
  )
}
