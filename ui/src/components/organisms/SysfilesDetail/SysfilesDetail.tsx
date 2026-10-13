import { Button } from '../../atoms/Button/Button'
import { Muted } from '../../atoms/Muted/Muted'
import { Pill } from '../../atoms/Pill/Pill'
import { Spinner } from '../../atoms/Spinner/Spinner'
import { READINESS, type Readiness } from '../../molecules/SysfileRow/SysfileRow'
import { SysfileReqRow, type Requirement } from '../../molecules/SysfileReqRow/SysfileReqRow'
import { formatBytes } from '../../../lib/format/format'
import styles from './SysfilesDetail.module.css'

export type Staging = 'unknown' | 'nothing_to_stage' | 'absent' | 'outdated' | 'current'

export type SysfilesSystem = {
  readonly key: string
  readonly label: string
  readonly readiness: Readiness
  readonly emulator: string
  /** Null until the device has been read. */
  readonly emulatorSeen: boolean | null
  readonly package: string | null
  readonly onDevice: { readonly n: number; readonly bytes: number }
  readonly inStore: number
  readonly missing: readonly string[]
  readonly note: string
  readonly staging: Staging
  readonly stagingFolder: string
  readonly stagedAny: boolean
  readonly requirements: readonly Requirement[]
}

export type SysfilesDetailProps = {
  readonly system: SysfilesSystem
  readonly busy?: boolean
  readonly onStage: () => void
  readonly onUnstage: () => void
}

/** What staging can do now: add what is absent, update what is outdated; nothing else. */
export function stageAction(staging: Staging): 'Add' | 'Update' | null {
  return staging === 'absent' ? 'Add' : staging === 'outdated' ? 'Update' : null
}

const STAGING_WORDS: Readonly<Record<Staging, string>> = {
  unknown: 'not read',
  nothing_to_stage: 'nothing to stage',
  absent: 'not staged',
  outdated: 'outdated',
  current: 'current',
}

function installedLine(s: SysfilesSystem): string {
  if (s.readiness === 'missing') return `Missing: ${s.missing.join(', ')}`
  if (s.readiness === 'unseen')
    return `${s.emulator} has not written any app data where USB can see it, so its install folder cannot be read; the games and staged files are unaffected`
  if (s.readiness === 'unknown') return 'Press Refresh from device'
  return READINESS[s.readiness][1]
}

/**
 * One system's files on the device (F11-S33): its emulator, its games, what
 * it needs, what is staged and installed, and staging them or removing them.
 */
export function SysfilesDetail({
  system: s,
  busy = false,
  onStage,
  onUnstage,
}: SysfilesDetailProps) {
  const [tone, word] = READINESS[s.readiness]
  const action = stageAction(s.staging)
  const pillTone = tone === 'neutral' ? 'neutral' : tone
  return (
    <article className={styles.detail} aria-labelledby={`sf-${s.key}`}>
      <h2 id={`sf-${s.key}`} className={styles.heading}>
        {s.label} <Muted>{s.key}</Muted> <Pill tone={pillTone}>{word}</Pill>
        {s.requirements.length > 0 && (
          <span className={styles.actions}>
            <Button
              variant="primary"
              small
              disabled={!action || busy}
              title={`Copy this system's files from the store into ${s.stagingFolder}`}
              onClick={onStage}
            >
              {busy ? <Spinner label="Working" /> : (action ?? 'Add')}
            </Button>
            <Button
              small
              disabled={!s.stagedAny || busy}
              title={`Delete this system's files from ${s.stagingFolder}`}
              onClick={onUnstage}
            >
              Remove
            </Button>
          </span>
        )}
      </h2>
      <dl className={styles.kv}>
        <dt>Emulator</dt>
        <dd>
          {s.emulator}{' '}
          {s.emulatorSeen === false ? (
            <>
              <Pill>not seen over USB</Pill>{' '}
              <Muted>open it once on the device, then Refresh from device</Muted>
            </>
          ) : s.emulatorSeen ? (
            <>
              <Pill tone="ok">installed</Pill> <Muted>{s.package ?? ''}</Muted>
            </>
          ) : null}
        </dd>
        <dt>Games on device</dt>
        <dd>
          {s.onDevice.n.toLocaleString()} · {formatBytes(s.onDevice.bytes)}{' '}
          <Muted>({s.inStore.toLocaleString()} in the store)</Muted>
        </dd>
        <dt>Installed</dt>
        <dd>
          {installedLine(s)}
          {s.note && <div className={styles.note}>{s.note}</div>}
        </dd>
        {s.requirements.length > 0 && (
          <>
            <dt>Staged</dt>
            <dd>
              {STAGING_WORDS[s.staging]} <Muted>in {s.stagingFolder}</Muted>
            </dd>
          </>
        )}
      </dl>
      {s.requirements.length > 0 && (
        <table className={styles.req}>
          <caption className={styles.caption}>Files {s.label} needs</caption>
          <thead>
            <tr>
              <th scope="col">Item</th>
              <th scope="col">Need</th>
              <th scope="col">Store</th>
              <th scope="col">Staged</th>
              <th scope="col">Installed</th>
            </tr>
          </thead>
          <tbody>
            {s.requirements.map((r) => (
              <SysfileReqRow key={r.name} req={r} />
            ))}
          </tbody>
        </table>
      )}
    </article>
  )
}
