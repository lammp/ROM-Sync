import { Button } from '../../atoms/Button/Button'
import { Muted } from '../../atoms/Muted/Muted'
import { DataTable } from '../../molecules/DataTable/DataTable'
import { formatBytes } from '../../../lib/format/format'

export type MaintenanceRow = {
  readonly action: string
  readonly label: string
  readonly what: string
  /** What a run would remove now, from its dry run; null until read. */
  readonly count: number | null
  readonly bytes: number
  readonly onRun: () => void
}

/**
 * The data folder's upkeep (SETTINGS.md section 6): each action with what
 * its dry run says it would remove, and Run, which the page confirms with
 * that count. Nothing to remove disables it.
 */
export function MaintenanceTable({
  rows,
  busy = false,
}: {
  rows: readonly MaintenanceRow[]
  busy?: boolean
}) {
  return (
    <DataTable
      caption="Upkeep"
      columns={[
        {
          key: 'what',
          label: 'Action',
          cell: (r: MaintenanceRow) => (
            <>
              {r.label}
              <div>
                <Muted>{r.what}</Muted>
              </div>
            </>
          ),
        },
        {
          key: 'now',
          label: 'Would remove',
          numeric: true,
          cell: (r: MaintenanceRow) =>
            r.count === null
              ? 'checking…'
              : `${r.count.toLocaleString()} · ${formatBytes(r.bytes)}`,
        },
        {
          key: 'run',
          label: 'Run',
          cell: (r: MaintenanceRow) => (
            <Button small disabled={busy || !r.count} onClick={r.onRun}>
              {r.label}
            </Button>
          ),
        },
      ]}
      rows={rows}
      rowKey={(r) => r.action}
    />
  )
}
