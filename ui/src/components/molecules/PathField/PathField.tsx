import { useId } from 'react'
import { ActionLink } from '../../atoms/ActionLink/ActionLink'
import { TextInput } from '../../atoms/TextInput/TextInput'
import styles from './PathField.module.css'

export type PathFieldProps = {
  readonly label: string
  /** The chosen path; empty when none is. */
  readonly value: string
  /** A folder to choose, or a file (the ADB executable). */
  readonly kind: 'folder' | 'file'
  readonly help?: string
  readonly error?: string
  /**
   * Opens the chooser: the window's own folder dialog, or the folder browser.
   * Absent only where the page may not read this computer (a bind off
   * loopback), where the path is typed instead.
   */
  readonly onChoose?: () => void
  /** Clearing the path, and typing one where nothing can be chosen. */
  readonly onChange: (value: string) => void
}

/**
 * A setting that names a place on this computer (F11-S45). The path is
 * chosen, never typed: the field is a button that opens the chooser, showing
 * what is chosen, with Clear beside it. Only where nothing can be chosen does
 * it fall back to a text field, and it says why.
 */
export function PathField({ label, value, kind, help, error, onChoose, onChange }: PathFieldProps) {
  const id = useId()
  if (!onChoose) {
    return (
      <TextInput
        label={label}
        value={value}
        onChange={onChange}
        error={error}
        help={[help, `Type the full path: a ${kind} can be chosen only on this computer.`]
          .filter(Boolean)
          .join(' ')}
      />
    )
  }
  const helpId = `${id}-help`
  const errorId = `${id}-error`
  const none = kind === 'folder' ? 'No folder chosen' : 'No file chosen'
  return (
    <span className={styles.field}>
      <span id={`${id}-label`} className={styles.label}>
        {label}
      </span>
      <span className={styles.row}>
        <button
          type="button"
          className={styles.path}
          aria-labelledby={`${id}-label ${id}-value ${id}-choose`}
          aria-describedby={
            [help && helpId, error && errorId].filter(Boolean).join(' ') || undefined
          }
          data-invalid={error ? true : undefined}
          onClick={onChoose}
        >
          <span id={`${id}-value`} className={value ? styles.value : styles.none}>
            {value || none}
          </span>{' '}
          <span id={`${id}-choose`} className={styles.choose}>
            {kind === 'folder' ? 'Choose folder…' : 'Choose file…'}
          </span>
        </button>
        {value && (
          <ActionLink onClick={() => onChange('')}>{`clear ${label.toLowerCase()}`}</ActionLink>
        )}
      </span>
      {help && (
        <span id={helpId} className={styles.help}>
          {help}
        </span>
      )}
      {error && (
        <span id={errorId} className={styles.error}>
          {error}
        </span>
      )}
    </span>
  )
}
