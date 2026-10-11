import { useId } from 'react'
import styles from './TextInput.module.css'

export type TextInputProps = {
  readonly label: string
  readonly value: string
  readonly onChange: (value: string) => void
  /** Shown under the field and announced with it. */
  readonly error?: string
  readonly placeholder?: string
  /** The label is still announced, only not drawn. */
  readonly hideLabel?: boolean
  readonly disabled?: boolean
  readonly inputMode?: 'text' | 'numeric' | 'url'
}

/** A single-line text field, always with a programmatically associated label. */
export function TextInput({
  label,
  value,
  onChange,
  error,
  placeholder,
  hideLabel = false,
  disabled,
  inputMode,
}: TextInputProps) {
  const id = useId()
  const errorId = `${id}-error`
  return (
    <span className={styles.field}>
      <label htmlFor={id} className={hideLabel ? styles.hidden : styles.label}>
        {label}
      </label>
      <input
        id={id}
        type="text"
        className={styles.input}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        inputMode={inputMode}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        onChange={(e) => onChange(e.target.value)}
      />
      {error && (
        <span id={errorId} className={styles.error}>
          {error}
        </span>
      )}
    </span>
  )
}
