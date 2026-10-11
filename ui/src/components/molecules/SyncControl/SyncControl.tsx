import { formatEta } from '../../../lib/format/format'
import type { Reading } from '../../../lib/progress/progress'
import { Button } from '../../atoms/Button/Button'
import { Spinner } from '../../atoms/Spinner/Spinner'
import styles from './SyncControl.module.css'

export type SyncState =
  | { readonly kind: 'idle'; readonly onSync: () => void }
  /** Not connected, or another job holds the device: the reason is shown, not only implied. */
  | { readonly kind: 'disabled'; readonly reason: string }
  /** A sync is running; `reading` is null until its first poll. */
  | { readonly kind: 'running'; readonly reading: Reading | null }

/** Sync, as a button, or the progress of the sync under way. One component, mounted in both places. */
export function SyncControl({ state }: { state: SyncState }) {
  if (state.kind === 'idle')
    return (
      <Button variant="primary" title="Make the device match the selection" onClick={state.onSync}>
        Sync
      </Button>
    )
  if (state.kind === 'disabled')
    return (
      <span className={styles.disabled}>
        <Button disabled title={state.reason}>
          Sync
        </Button>
        <span className={styles.reason}>{state.reason}</span>
      </span>
    )
  const r = state.reading
  return (
    <span className={styles.syncing} role="status" title={r?.tip}>
      <Spinner label="Syncing" />
      {r ? (
        <>
          <b>{r.pct}%</b>
          <span className={styles.muted}>
            ETA {formatEta(r.eta)} · {r.phase}
          </span>
        </>
      ) : (
        <span className={styles.muted}>starting…</span>
      )}
    </span>
  )
}
