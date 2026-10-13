import { Muted } from '../../atoms/Muted/Muted'
import { Pill } from '../../atoms/Pill/Pill'
import { DataTable } from '../../molecules/DataTable/DataTable'
import { formatBytes } from '../../../lib/format/format'

export type StoreItem = {
  readonly system: string
  readonly label: string
  readonly emulator: string
  readonly name: string
  readonly required: boolean
  readonly present: boolean
  readonly size: number | null
  readonly verified: boolean | null
  readonly note: string
}

/** The store's copy in words: its size, and whether it is a known dump. */
export function storeWord(i: StoreItem): readonly ['ok' | 'warn' | 'bad', string] {
  if (!i.present) return ['bad', 'missing']
  const size = i.size != null ? formatBytes(i.size) : 'present'
  if (i.verified === true) return ['ok', `${size} verified`]
  if (i.verified === false) return ['warn', `${size} not a known dump`]
  return ['ok', size]
}

/**
 * Every system file the registry knows, with the store's copy only (F11-S33):
 * what the page shows with no device chosen.
 */
export function SysfilesStore({ items }: { items: readonly StoreItem[] }) {
  return (
    <DataTable
      caption="System files in the store"
      columns={[
        { key: 'system', label: 'System', cell: (i: StoreItem) => i.label },
        { key: 'emu', label: 'Emulator', cell: (i: StoreItem) => i.emulator },
        { key: 'file', label: 'File', cell: (i: StoreItem) => i.name },
        {
          key: 'need',
          label: 'Need',
          cell: (i: StoreItem) => (i.required ? 'required' : 'optional'),
        },
        {
          key: 'store',
          label: 'Store',
          cell: (i: StoreItem) => {
            const [tone, word] = storeWord(i)
            return <Pill tone={tone}>{word}</Pill>
          },
        },
        { key: 'note', label: 'Note', cell: (i: StoreItem) => <Muted>{i.note}</Muted> },
      ]}
      rows={items}
      rowKey={(i) => `${i.system}/${i.name}`}
      empty="The registry lists no system files."
    />
  )
}
