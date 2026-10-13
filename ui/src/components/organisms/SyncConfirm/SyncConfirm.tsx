import { useState } from 'react'
import { Button } from '../../atoms/Button/Button'
import { Checkbox } from '../../atoms/Checkbox/Checkbox'
import { Muted } from '../../atoms/Muted/Muted'
import { DataTable } from '../../molecules/DataTable/DataTable'
import type { PlanOp } from '../../molecules/PlanLine/PlanLine'
import { formatBytes } from '../../../lib/format/format'
import { Modal } from '../Modal/Modal'
import styles from './SyncConfirm.module.css'

export type SyncPlan = {
  readonly send: readonly PlanOp[]
  readonly update: readonly PlanOp[]
  readonly remove: readonly PlanOp[]
  readonly unchanged: number
  readonly bytes: { readonly net: number; readonly free: number | null }
}

export type SyncConfirmProps = {
  readonly name: string
  readonly plan: SyncPlan
  readonly busy?: boolean
  readonly onStart: () => void
  readonly onCancel: () => void
}

type Line = { readonly label: string; readonly n: number; readonly size: string }

const sum = (ops: readonly PlanOp[]) => formatBytes(ops.reduce((a, o) => a + o.size, 0))

/** The rows version 1's sync dialog showed: only what the sync will do, then what stays. */
export function lines(plan: SyncPlan): Line[] {
  const out: Line[] = []
  if (plan.send.length) out.push({ label: 'Send', n: plan.send.length, size: sum(plan.send) })
  if (plan.update.length)
    out.push({ label: 'Replace', n: plan.update.length, size: sum(plan.update) })
  if (plan.remove.length)
    out.push({ label: 'Remove from device', n: plan.remove.length, size: sum(plan.remove) })
  out.push({ label: 'Already in place', n: plan.unchanged, size: '' })
  return out
}

/**
 * What a sync will do, asked before it starts (F11-S32). A sync that removes
 * anything waits for the person to tick that they mean those removals, by
 * number, before Start can be pressed (F16-S2); if the engine's plan has
 * changed since, it refuses and the dialog is asked again.
 */
export function SyncConfirm({ name, plan, busy = false, onStart, onCancel }: SyncConfirmProps) {
  const b = plan.bytes
  const removing = plan.remove.length
  const [meant, setMeant] = useState(false)
  return (
    <Modal title={`Sync ${name}`} onClose={onCancel}>
      <div className={styles.body}>
        <Muted>
          Makes the device&apos;s game folders match your selection. Games only; nothing is wiped.
        </Muted>
        <DataTable
          caption="What the sync will do"
          columns={[
            { key: 'what', label: 'Action', cell: (l: Line) => l.label },
            { key: 'n', label: 'Games', numeric: true, cell: (l: Line) => l.n.toLocaleString() },
            { key: 'size', label: 'Size', numeric: true, cell: (l: Line) => l.size },
          ]}
          rows={lines(plan)}
          rowKey={(l) => l.label}
        />
        <Muted>
          Net change {formatBytes(b.net)}
          {b.free != null &&
            ` · ${formatBytes(b.free)} free now, ${formatBytes(b.free - b.net)} after`}
        </Muted>
        {removing > 0 && (
          <Checkbox
            label={`Remove ${removing.toLocaleString()} game${removing === 1 ? '' : 's'} from ${name}`}
            checked={meant}
            onChange={setMeant}
          />
        )}
      </div>
      <div className={styles.actions}>
        <Button onClick={onCancel}>Cancel</Button>
        <Button variant="primary" disabled={busy || (removing > 0 && !meant)} onClick={onStart}>
          {busy ? 'Starting…' : 'Start'}
        </Button>
      </div>
    </Modal>
  )
}
