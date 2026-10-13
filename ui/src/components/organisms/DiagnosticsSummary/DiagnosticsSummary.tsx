import { Muted } from '../../atoms/Muted/Muted'
import { formatBytes } from '../../../lib/format/format'
import styles from './DiagnosticsSummary.module.css'

export type LastSyncFact = {
  readonly device: string
  readonly started: string
  readonly state: string
  readonly counts: Readonly<Record<string, number | string>>
  readonly bytes: number | null
}

export type ErrorFact = {
  readonly job: string
  readonly kind: string
  readonly finished: string | null
  readonly code: string | null
  readonly message: string | null
}

export type DiagnosticsSummaryProps = {
  /** "ROM-Sync 2.0.0 · API v1". */
  readonly version: string
  /** Where the page runs: "desktop window" or "browser". */
  readonly host: string
  readonly address: string
  readonly dataFolder: string
  readonly logFolder: string
  readonly lastSync: LastSyncFact | null
  readonly errors: readonly ErrorFact[]
  /** The support bundle's address (F15-S3): the settings with every secret left out. */
  readonly bundleHref?: string
}

const when = (iso: string | null) => (iso ? iso.slice(0, 16).replace('T', ' ') : '')

function syncWords(s: LastSyncFact): string {
  const counts = Object.entries(s.counts).map(([k, v]) => `${k} ${v}`)
  const bytes = s.bytes != null ? [formatBytes(s.bytes)] : []
  return [s.device, when(s.started), s.state, ...counts, ...bytes].join(' · ')
}

/**
 * What the Diagnostics section says about the engine (F15-S1, SETTINGS.md
 * section 7): its version and shell, the address the page reached, its
 * folders, the last sync and the jobs that failed most recently.
 */
export function DiagnosticsSummary(p: DiagnosticsSummaryProps) {
  return (
    <>
      <dl className={styles.facts} aria-label="Diagnostics">
        <dt>Version</dt>
        <dd>{p.version}</dd>
        <dt>Shell</dt>
        <dd>{p.host}</dd>
        <dt>Address</dt>
        <dd>{p.address}</dd>
        <dt>Data folder</dt>
        <dd>{p.dataFolder}</dd>
        <dt>Log folder</dt>
        <dd>{p.logFolder}</dd>
        <dt>Last sync</dt>
        <dd>{p.lastSync ? syncWords(p.lastSync) : <Muted>no sync yet</Muted>}</dd>
      </dl>
      {p.bundleHref && (
        <p>
          <a href={p.bundleHref} download="romsync-support.zip">
            Export a support bundle
          </a>{' '}
          <Muted>settings with every secret left out, recent jobs and the logs</Muted>
        </p>
      )}
      <h3>Recent errors</h3>
      {p.errors.length === 0 ? (
        <Muted>No job has failed.</Muted>
      ) : (
        <ul className={styles.errors} aria-label="Recent errors">
          {p.errors.map((e) => (
            <li key={e.job}>
              {e.kind} · {when(e.finished)}
              {e.code ? ` · ${e.code}` : ''}
              {e.message && <pre className={styles.message}>{e.message}</pre>}
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
