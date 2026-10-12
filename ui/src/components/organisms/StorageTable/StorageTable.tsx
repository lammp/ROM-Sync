import { DataTable } from '../../molecules/DataTable/DataTable'
import { formatBytes } from '../../../lib/format/format'

export type StoragePart = {
  readonly component: string
  readonly files: number
  readonly bytes: number
  readonly reclaimable: number
}

/** Each part of the data folder in the words the page uses. */
export const PARTS: Readonly<Record<string, string>> = {
  database: 'Database',
  covers: 'Covers',
  cache: 'Screenshot and artwork cache',
  logs: 'Logs',
  runs: 'Sync run folders',
  working: 'Working files',
  webview: 'Embedded browser profile',
}

const share = (part: number, total: number) =>
  total === 0 ? '' : `${Math.round((part / total) * 100)}%`

/**
 * The storage breakdown (F15-S2, SETTINGS.md section 6): each part of the
 * data folder with its files and size, every subfolder counted, its share of
 * the whole, and what its upkeep action would reclaim now.
 */
export function StorageTable({ parts }: { parts: readonly StoragePart[] }) {
  const total = parts.reduce((n, p) => n + p.bytes, 0)
  const back = parts.reduce((n, p) => n + p.reclaimable, 0)
  return (
    <DataTable
      caption={`Storage: ${formatBytes(total)}, ${formatBytes(back)} reclaimable`}
      columns={[
        { key: 'part', label: 'Part', cell: (p: StoragePart) => PARTS[p.component] ?? p.component },
        {
          key: 'files',
          label: 'Files',
          numeric: true,
          cell: (p: StoragePart) => p.files.toLocaleString(),
        },
        {
          key: 'size',
          label: 'Size',
          numeric: true,
          cell: (p: StoragePart) => formatBytes(p.bytes),
        },
        {
          key: 'share',
          label: 'Share',
          numeric: true,
          cell: (p: StoragePart) => share(p.bytes, total),
        },
        {
          key: 'back',
          label: 'Reclaimable',
          numeric: true,
          cell: (p: StoragePart) => (p.reclaimable ? formatBytes(p.reclaimable) : ''),
        },
      ]}
      rows={parts}
      rowKey={(p) => p.component}
      empty="Nothing measured yet."
    />
  )
}
