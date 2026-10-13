import { useEffect, useId, useRef } from 'react'
import { IconButton } from '../../atoms/IconButton/IconButton'
import { Icon } from '../../atoms/Icon/Icon'
import styles from './LockedField.module.css'

export type LockedFieldProps = {
  readonly label: string
  readonly value: string
  readonly onChange: (value: string) => void
  /** Saved and not being changed: shown, not editable, until the edit icon is pressed. */
  readonly locked: boolean
  readonly onUnlock: () => void
  /** Offered once opened: drop what was typed and lock the saved value again. */
  readonly onLock?: () => void
  readonly help?: string
  readonly error?: string
  readonly placeholder?: string
  readonly inputMode?: 'text' | 'numeric'
}

/**
 * A saved value that is changed on purpose (F11-S51): once saved it is
 * locked, with an edit icon at its end that opens it again, and once open an
 * undo icon that puts the saved value back. An empty field is open, because
 * there is nothing to protect.
 */
export function LockedField({
  label,
  value,
  onChange,
  locked,
  onUnlock,
  onLock,
  help,
  error,
  placeholder,
  inputMode,
}: LockedFieldProps) {
  const id = useId()
  const input = useRef<HTMLInputElement>(null)
  const was = useRef(locked)
  // opened by its edit icon: the caret goes where the typing will
  useEffect(() => {
    if (was.current && !locked) input.current?.focus()
    was.current = locked
  }, [locked])
  const describedBy =
    [help && `${id}-help`, error && `${id}-error`].filter(Boolean).join(' ') || undefined
  return (
    <span className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <span className={styles.box} data-locked={locked || undefined}>
        <input
          ref={input}
          id={id}
          type="text"
          className={styles.input}
          value={value}
          readOnly={locked}
          placeholder={placeholder}
          inputMode={inputMode}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          onChange={(e) => onChange(e.target.value)}
        />
        {locked && (
          <IconButton label={`Change ${label}`} onClick={onUnlock}>
            <Icon name="edit" />
          </IconButton>
        )}
        {!locked && onLock && (
          <IconButton label={`Keep the saved ${label}`} onClick={onLock}>
            <Icon name="undo" />
          </IconButton>
        )}
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
