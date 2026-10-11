import { Muted } from '../../atoms/Muted/Muted'
import { DataTable } from '../../molecules/DataTable/DataTable'
import { formatBytes } from '../../../lib/format/format'

export type Fate =
  /** In a managed system: the next sync removes it. */
  | { readonly kind: 'removed' }
  /** In a system the sync leaves alone, or one the store does not have. */
  | { readonly kind: 'left'; readonly why: string }

export type Orphan = {
  readonly system: string
  readonly name: string
  readonly kind: string
  readonly size: number | null
  readonly fate: Fate
}

/** What happens to an item only the device holds, in the words version 1 used. */
export function fateWords(f: Fate): string {
  return f.kind === 'removed'
    ? 'not in the store, so the next sync removes it from the device'
    : `left alone: ${f.why}`
}

/**
 * One device's items that the store has no copy of (F11-S39), each with what
 * the next sync will do to it.
 */
export function RecoverTable({ device, items }: { device: string; items: readonly Orphan[] }) {
  return (
    <DataTable
      caption={`On ${device}, not in the store`}
      columns={[
        {
          key: 'item',
          label: 'Item',
          cell: (o: Orphan) => (
            <>
              {o.system} \ <b>{o.name}</b>
              {o.kind === 'folder' && <Muted> (folder)</Muted>}
            </>
          ),
        },
        {
          key: 'size',
          label: 'Size',
          numeric: true,
          cell: (o: Orphan) => (o.size == null ? '' : formatBytes(o.size)),
        },
        {
          key: 'fate',
          label: 'Next sync',
          cell: (o: Orphan) => <Muted>{fateWords(o.fate)}</Muted>,
        },
      ]}
      rows={items}
      rowKey={(o) => `${o.system}\\${o.name}`}
      empty="Everything on this device is in the store."
    />
  )
}
