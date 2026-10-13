import { Button } from '../../atoms/Button/Button'
import { Muted } from '../../atoms/Muted/Muted'
import { Pill } from '../../atoms/Pill/Pill'
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
  /** The store's folder already has this name: recovering it was refused, and nothing was replaced. */
  readonly clash?: boolean
}

export const orphanKey = (o: { readonly system: string; readonly name: string }) =>
  `${o.system}\\${o.name}`

/** What happens to an item only the device holds, in the words version 1 used. */
export function fateWords(f: Fate): string {
  return f.kind === 'removed'
    ? 'not in the store, so the next sync removes it from the device'
    : `left alone: ${f.why}`
}

export type RecoverTableProps = {
  readonly device: string
  readonly items: readonly Orphan[]
  /** Pulls one item back into the store (F11-S40); absent while the device is busy elsewhere. */
  readonly onRecover?: (item: Orphan) => void
  /** The item being recovered; every Recover waits while one runs. */
  readonly busy?: string | null
}

function action(o: Orphan, onRecover: RecoverTableProps['onRecover'], busy: string | null) {
  if (o.clash) return <Pill tone="warn">the store already has this name</Pill>
  if (o.kind === 'folder') return <Muted>folders are not recovered</Muted>
  if (!onRecover) return null
  const mine = busy === orphanKey(o)
  return (
    <Button
      small
      disabled={busy !== null}
      aria-label={`${mine ? 'Recovering' : 'Recover'} ${o.name}`}
      onClick={() => onRecover(o)}
    >
      {mine ? 'Recovering…' : 'Recover'}
    </Button>
  )
}

/**
 * One device's items that the store has no copy of (F11-S39), each with what
 * the next sync will do to it, and Recover, which pulls a file back into the
 * store and never over a file the store already has (F11-S40).
 */
export function RecoverTable({ device, items, onRecover, busy = null }: RecoverTableProps) {
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
        { key: 'act', label: 'Recover', cell: (o: Orphan) => action(o, onRecover, busy) },
      ]}
      rows={items}
      rowKey={orphanKey}
      empty="Everything on this device is in the store."
    />
  )
}
