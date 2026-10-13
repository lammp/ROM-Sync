import { formatBytes } from '../../../lib/format/format'
import { Pill, type Tone } from '../../atoms/Pill/Pill'
import styles from './SysfileReqRow.module.css'

export type Staged = 'unknown' | 'absent' | 'current' | 'different' | 'present'
export type Installed =
  'unknown' | 'not_applicable' | 'unseen' | 'missing' | 'different' | 'installed'

/** The two device-side vocabularies, each state with its tone and its word. */
export const STAGED: Readonly<Record<Staged, readonly [Tone, string]>> = {
  current: ['ok', 'current'],
  present: ['ok', 'staged'],
  different: ['warn', 'different version'],
  absent: ['bad', 'not staged'],
  unknown: ['neutral', 'not read'],
}
export const INSTALLED: Readonly<Record<Installed, readonly [Tone, string]>> = {
  installed: ['ok', 'installed'],
  different: ['warn', 'different version'],
  missing: ['bad', 'not installed'],
  unseen: ['neutral', 'not visible'],
  not_applicable: ['neutral', 'n/a'],
  unknown: ['neutral', 'not read'],
}

export type Requirement = {
  readonly name: string
  /** The name it is staged under, when that differs. */
  readonly stagedName: string
  readonly note: string
  readonly required: boolean
  /** One of a group, any of which will do. */
  readonly group: boolean
  readonly store: {
    readonly present: boolean
    readonly size: number | null
    readonly verified: boolean | null
  }
  readonly staged: Staged
  readonly installed: Installed
  readonly installedPath: string
}

function storeCell(s: Requirement['store']) {
  if (!s.present) return <Pill tone="bad">not in store</Pill>
  const size = s.size != null ? formatBytes(s.size) : 'present'
  const check = s.verified === true ? ' verified' : s.verified === false ? ' not a known dump' : ''
  return <Pill tone={s.verified === false ? 'warn' : 'ok'}>{size + check}</Pill>
}

/** One required or optional file for a system: the store's copy, the staged copy, the installed one. */
export function SysfileReqRow({ req }: { req: Requirement }) {
  const [stagedTone, stagedWord] = STAGED[req.staged]
  const [instTone, instWord] = INSTALLED[req.installed]
  return (
    <tr>
      <td>
        <b>{req.name}</b>
        {req.stagedName !== req.name && <span className={styles.muted}> {req.stagedName}</span>}
        {req.note && <div className={styles.muted}>{req.note}</div>}
      </td>
      <td>
        {req.required ? 'required' : 'optional'}
        {req.group && <span className={styles.muted}> (any one)</span>}
      </td>
      <td>{storeCell(req.store)}</td>
      <td>
        <Pill tone={stagedTone}>{stagedWord}</Pill>
      </td>
      <td>
        <Pill tone={instTone}>{instWord}</Pill>
        {req.installedPath && (
          <div className={[styles.muted, styles.sm].join(' ')}>{req.installedPath}</div>
        )}
      </td>
    </tr>
  )
}
