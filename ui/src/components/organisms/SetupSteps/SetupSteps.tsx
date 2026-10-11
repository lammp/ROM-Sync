import { Button } from '../../atoms/Button/Button'
import { Dot } from '../../atoms/Dot/Dot'
import { Muted } from '../../atoms/Muted/Muted'
import styles from './SetupSteps.module.css'

export type SetupStep = {
  readonly label: string
  readonly done: boolean
  readonly action: { readonly label: string; readonly onClick: () => void }
  readonly note?: string
}

export type SetupStepsProps = {
  readonly steps: readonly SetupStep[]
  readonly onDismiss: () => void
}

/**
 * Section 0 of the settings page (SETTINGS.md): the first-run steps in order,
 * each saying whether it is done, shown while any is not. Once all are, a
 * single line that can be dismissed.
 */
export function SetupSteps({ steps, onDismiss }: SetupStepsProps) {
  if (steps.every((s) => s.done))
    return (
      <p className={styles.complete} role="status">
        Setup complete.{' '}
        <Button small onClick={onDismiss}>
          Dismiss
        </Button>
      </p>
    )
  return (
    <ol className={styles.steps} aria-label="Setup">
      {steps.map((s) => (
        <li key={s.label} className={styles.step}>
          <Dot tone={s.done ? 'ok' : 'warn'} />
          <span className={styles.label}>
            {s.label} <Muted>{s.done ? 'done' : 'to do'}</Muted>
            {s.note && <div className={styles.note}>{s.note}</div>}
          </span>
          {!s.done && (
            <Button small onClick={s.action.onClick}>
              {s.action.label}
            </Button>
          )}
        </li>
      ))}
    </ol>
  )
}
