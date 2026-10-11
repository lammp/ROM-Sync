import { Pill, type Tone } from '../../atoms/Pill/Pill'
import { DataTable, type Column } from '../../molecules/DataTable/DataTable'
import { formatBytes } from '../../../lib/format/format'

export type Run = {
  readonly id: number
  readonly started: string
  readonly state: string
  readonly counts: Readonly<Record<string, number | string>> | null
  readonly bytesMoved: number | null
}

/** Each run state as a word and a tone; the word is what is read. */
export const RUN_STATES: Readonly<Record<string, readonly [Tone, string]>> = {
  running: ['neutral', 'running'],
  done: ['ok', 'done'],
  failed: ['bad', 'failed'],
  cancelled: ['warn', 'cancelled'],
  interrupted: ['bad', 'interrupted'],
}

const count = (r: Run, key: string) => {
  const v = r.counts?.[key]
  return typeof v === 'number' ? v.toLocaleString() : ''
}

/** A device's sync runs, newest first (F11-S32), as version 1's history table. */
export function RunHistory({ runs }: { runs: readonly Run[] }) {
  const columns: Column<Run>[] = [
    { key: 'run', label: 'Run', cell: (r) => `#${r.id}` },
    { key: 'started', label: 'Started', cell: (r) => r.started.slice(0, 16).replace('T', ' ') },
    {
      key: 'state',
      label: 'State',
      cell: (r) => {
        const [tone, word] = RUN_STATES[r.state] ?? ['neutral', r.state]
        return <Pill tone={tone}>{word}</Pill>
      },
    },
    { key: 'sent', label: 'Sent', numeric: true, cell: (r) => count(r, 'send') },
    { key: 'replaced', label: 'Replaced', numeric: true, cell: (r) => count(r, 'update') },
    { key: 'removed', label: 'Removed', numeric: true, cell: (r) => count(r, 'remove') },
    {
      key: 'failed',
      label: 'Failed',
      numeric: true,
      cell: (r) => {
        const n = r.counts?.failed
        return typeof n === 'number' && n > 0 ? <Pill tone="bad">{n.toLocaleString()}</Pill> : ''
      },
    },
    {
      key: 'moved',
      label: 'Moved',
      numeric: true,
      cell: (r) => (r.bytesMoved == null ? '' : formatBytes(r.bytesMoved)),
    },
  ]
  return (
    <DataTable
      caption="History"
      columns={columns}
      rows={runs}
      rowKey={(r) => String(r.id)}
      empty="no runs yet"
    />
  )
}
