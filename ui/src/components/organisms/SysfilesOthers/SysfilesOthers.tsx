import { Button } from '../../atoms/Button/Button'
import { Muted } from '../../atoms/Muted/Muted'
import { Pill } from '../../atoms/Pill/Pill'
import { DataTable } from '../../molecules/DataTable/DataTable'
import { formatBytes } from '../../../lib/format/format'

export type Stray = {
  readonly path: string
  readonly name: string
  readonly kind: string
  readonly size: number | null
}

export type SysfilesOthersProps = {
  readonly others: readonly Stray[]
  readonly stageRoot: string
  /** The item being removed, as path and name joined by "/". */
  readonly busy?: string | null
  readonly onRemove: (item: Stray) => void
}

export const strayKey = (s: Stray) => `${s.path}/${s.name}`

/**
 * Files under the staging root that belong to no system's set (F11-S33).
 * Remove deletes one from the device, after the page has asked.
 */
export function SysfilesOthers({ others, stageRoot, busy = null, onRemove }: SysfilesOthersProps) {
  return (
    <article aria-labelledby="sf-others">
      <h2 id="sf-others">
        Other files in {stageRoot} <Muted>{others.length.toLocaleString()}</Muted>
      </h2>
      <Muted>
        Files under the staging folder that belong to no system&apos;s set. Remove deletes the file
        from the device.
      </Muted>
      {others.length === 0 ? (
        <p>
          <Pill tone="ok">nothing stray</Pill>
        </p>
      ) : (
        <DataTable
          caption="Stray files"
          columns={[
            { key: 'folder', label: 'Folder', cell: (s: Stray) => <Muted>{s.path}</Muted> },
            {
              key: 'name',
              label: 'Name',
              cell: (s: Stray) => (
                <>
                  <b>{s.name}</b>
                  {s.kind === 'folder' && <Muted> (folder)</Muted>}
                </>
              ),
            },
            {
              key: 'size',
              label: 'Size',
              numeric: true,
              cell: (s: Stray) => (s.kind === 'folder' ? '' : formatBytes(s.size)),
            },
            {
              key: 'act',
              label: 'Action',
              cell: (s: Stray) => (
                <Button
                  small
                  disabled={busy !== null}
                  aria-label={`${busy === strayKey(s) ? 'Removing' : 'Remove'} ${s.name}`}
                  onClick={() => onRemove(s)}
                >
                  {busy === strayKey(s) ? 'Removing…' : 'Remove'}
                </Button>
              ),
            },
          ]}
          rows={others}
          rowKey={strayKey}
        />
      )}
    </article>
  )
}
