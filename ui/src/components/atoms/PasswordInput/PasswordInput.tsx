import { useId } from 'react'
import styles from './PasswordInput.module.css'

export type PasswordInputProps = {
  readonly label: string
  /** What has been typed in this session; a stored secret is never passed in. */
  readonly value: string
  readonly onChange: (value: string) => void
  /** Whether a secret is already stored, which the placeholder says. */
  readonly stored: boolean
}

/** A secret field. It knows only whether a secret is stored, never the secret. */
export function PasswordInput({ label, value, onChange, stored }: PasswordInputProps) {
  const id = useId()
  return (
    <span className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <input
        id={id}
        type="password"
        className={styles.input}
        value={value}
        autoComplete="off"
        placeholder={stored ? 'Stored. Type to replace.' : 'Not set'}
        onChange={(e) => onChange(e.target.value)}
      />
    </span>
  )
}
