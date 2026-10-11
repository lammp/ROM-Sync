import { Button } from '../../atoms/Button/Button'
import { Pill } from '../../atoms/Pill/Pill'
import styles from './LoadError.module.css'

export type LoadErrorProps = {
  /** What could not be read: "the library", "this device's system files". */
  readonly what: string
  readonly message: string
  readonly onRetry: () => void
  readonly retrying?: boolean
}

/**
 * A read that failed, said in place of what it would have shown, with Retry
 * (F11-S38): no view waits on a failed read for ever.
 */
export function LoadError({ what, message, onRetry, retrying = false }: LoadErrorProps) {
  return (
    <p className={styles.error} role="alert">
      <Pill tone="bad">could not read {what}</Pill>
      <span className={styles.message}>{message}</span>
      <Button small disabled={retrying} onClick={onRetry}>
        {retrying ? 'Retrying…' : 'Retry'}
      </Button>
    </p>
  )
}
