import { Button } from '../../atoms/Button/Button'
import { Pill, type Tone } from '../../atoms/Pill/Pill'
import { DataTable } from '../../molecules/DataTable/DataTable'

export type JobRow = {
  readonly id: string
  readonly kind: string
  readonly started: string | null
  readonly state: string
  readonly progress: {
    readonly phase: string
    readonly done: number
    readonly total: number | null
  } | null
  readonly error: string | null
}

export const JOB_STATES: Readonly<Record<string, readonly [Tone, string]>> = {
  queued: ['neutral', 'queued'],
  running: ['neutral', 'running'],
  cancelling: ['warn', 'cancelling'],
  done: ['ok', 'done'],
  failed: ['bad', 'failed'],
  cancelled: ['warn', 'cancelled'],
}

const ENDED = new Set(['done', 'failed', 'cancelled'])

export function progressText(p: JobRow['progress']): string {
  if (!p) return ''
  return p.total ? `${p.phase} ${p.done.toLocaleString()} of ${p.total.toLocaleString()}` : p.phase
}

/**
 * Every job the engine holds (SETTINGS.md section 7): what it is, when it
 * started, how far it has got, and a Cancel while it runs. Cancel stops after
 * the item in hand, never inside a copy.
 */
export function JobsTable({
  jobs,
  onCancel,
}: {
  jobs: readonly JobRow[]
  onCancel: (id: string) => void
}) {
  return (
    <DataTable
      caption="Jobs"
      columns={[
        { key: 'kind', label: 'Job', cell: (j: JobRow) => j.kind },
        {
          key: 'started',
          label: 'Started',
          cell: (j: JobRow) => (j.started ?? '').slice(0, 16).replace('T', ' '),
        },
        {
          key: 'state',
          label: 'State',
          cell: (j: JobRow) => {
            const [tone, word] = JOB_STATES[j.state] ?? ['neutral', j.state]
            return <Pill tone={tone}>{word}</Pill>
          },
        },
        {
          key: 'progress',
          label: 'Progress',
          cell: (j: JobRow) => (j.state === 'failed' ? (j.error ?? '') : progressText(j.progress)),
        },
        {
          key: 'act',
          label: 'Action',
          cell: (j: JobRow) =>
            ENDED.has(j.state) || j.state === 'cancelling' ? null : (
              <Button small aria-label={`Cancel ${j.kind}`} onClick={() => onCancel(j.id)}>
                Cancel
              </Button>
            ),
        },
      ]}
      rows={jobs}
      rowKey={(j) => j.id}
      empty="No jobs yet."
    />
  )
}
