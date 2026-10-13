import { Muted } from '../../atoms/Muted/Muted'
import { Pill } from '../../atoms/Pill/Pill'
import { DataTable, type Column } from '../../molecules/DataTable/DataTable'
import { SegmentedControl } from '../../molecules/SegmentedControl/SegmentedControl'
import { formatBytes } from '../../../lib/format/format'

export type Mode = 'all' | 'none' | 'off'

export type Tally = { readonly n: number; readonly bytes: number }

export type SystemRow = {
  readonly key: string
  readonly label: string
  /** Null for a folder on the device that is not a store system. */
  readonly store: Tally | null
  readonly device: Tally
  readonly mode: Mode
  /** Games chosen by hand against the system's mode. */
  readonly overrides: number
}

export type SystemsTableProps = {
  readonly rows: readonly SystemRow[]
  readonly onMode: (system: string, mode: Mode) => void
  readonly disabled?: boolean
}

/** What each mode does, said on the control rather than left to colour. */
export const MODES = [
  { value: 'all', label: 'all' },
  { value: 'none', label: 'none' },
  { value: 'off', label: 'left alone' },
] as const

/** An override's meaning depends on the mode it overrides, as version 1 wrote it. */
export function overrideWord(row: SystemRow): string {
  if (!row.overrides) return ''
  return `${row.overrides.toLocaleString()} ${row.mode === 'all' ? 'excluded' : 'picked'}`
}

/**
 * The device page's systems (F11-S32): what the store and the device hold of
 * each, and the system's selection mode. A folder on the device that is not
 * a store system is listed and left alone.
 */
export function SystemsTable({ rows, onMode, disabled = false }: SystemsTableProps) {
  const columns: Column<SystemRow>[] = [
    {
      key: 'system',
      label: 'System',
      cell: (r) =>
        r.store ? (
          <>
            {r.label} <Muted>{r.key}</Muted>
          </>
        ) : (
          <>
            {r.label} <Pill tone="warn">on device, not a store system: left alone</Pill>
          </>
        ),
    },
    {
      key: 'store-n',
      label: 'In store',
      numeric: true,
      cell: (r) => r.store?.n.toLocaleString() ?? '',
    },
    {
      key: 'store-b',
      label: 'Store size',
      numeric: true,
      cell: (r) => (r.store ? formatBytes(r.store.bytes) : ''),
    },
    { key: 'dev-n', label: 'On device', numeric: true, cell: (r) => r.device.n.toLocaleString() },
    { key: 'dev-b', label: 'Device size', numeric: true, cell: (r) => formatBytes(r.device.bytes) },
    {
      key: 'mode',
      label: 'Selection',
      cell: (r) =>
        r.store ? (
          <SegmentedControl
            label={`Selection for ${r.label}`}
            segments={MODES}
            value={r.mode}
            onChange={(m) => onMode(r.key, m)}
            disabled={disabled}
          />
        ) : null,
    },
    { key: 'over', label: 'Overrides', cell: overrideWord },
  ]
  return (
    <DataTable
      caption="Systems"
      columns={columns}
      rows={rows}
      rowKey={(r) => r.key}
      empty="No systems in the store yet."
    />
  )
}
