import styles from './JobLine.module.css'

export type JobState = 'queued' | 'running' | 'cancelling' | 'done' | 'failed' | 'cancelled'

export type JobLineProps = {
  readonly state: JobState
  readonly progress?: {
    readonly phase: string
    readonly done: number
    readonly total: number | null
    readonly current: string | null
  } | null
  /** What a finished job did, by name: added 3, updated 2. */
  readonly result?: Readonly<Record<string, number>> | null
  readonly error?: string | null
}

/** A job's result as a sentence, never as JSON (SPEC section 8). */
export function summarise(result: Readonly<Record<string, number>> | null | undefined): string {
  const parts = Object.entries(result ?? {}).map(
    ([k, n]) => `${k.replace(/_/g, ' ')} ${n.toLocaleString()}`,
  )
  return parts.length ? parts.join(', ') : 'nothing to do'
}

function sentence({ state, progress, result, error }: JobLineProps): string {
  switch (state) {
    case 'queued':
      return 'waiting to start…'
    case 'running': {
      if (!progress) return 'starting…'
      const count = progress.total
        ? ` ${progress.done.toLocaleString()} of ${progress.total.toLocaleString()}`
        : ''
      return `${progress.phase}${count}${progress.current ? ` · ${progress.current}` : ''}`
    }
    case 'cancelling':
      return 'stopping…'
    case 'done':
      return `done: ${summarise(result)}`
    case 'cancelled':
      return 'stopped'
    case 'failed':
      return `failed: ${(error ?? 'no reason given').split('\n')[0]}`
  }
}

/** One line under an action that runs as a job: how it is going, or how it went. */
export function JobLine(props: JobLineProps) {
  return (
    <div
      role="status"
      className={[styles.job, props.state === 'failed' && styles.bad].filter(Boolean).join(' ')}
    >
      {sentence(props)}
    </div>
  )
}
