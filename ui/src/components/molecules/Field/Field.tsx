import { useId, type ReactNode } from 'react'
import styles from './Field.module.css'

export type FieldProps = {
  readonly label: string
  /** Renders the control with the id its label points at, and the id of the help line. */
  readonly children: (ids: { readonly id: string; readonly describedBy?: string }) => ReactNode
  readonly help?: ReactNode
}

/** A label over its control, with an optional line of help tied to it. */
export function Field({ label, children, help }: FieldProps) {
  const id = useId()
  const helpId = `${id}-help`
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      {children({ id, describedBy: help ? helpId : undefined })}
      {help && (
        <div id={helpId} className={styles.help}>
          {help}
        </div>
      )}
    </div>
  )
}
