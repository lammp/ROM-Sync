import { useId, useState, type ReactNode } from 'react'
import { formatBytes } from '../../../lib/format/format'
import { ActionLink } from '../../atoms/ActionLink/ActionLink'
import { Pill } from '../../atoms/Pill/Pill'
import styles from './PlanLine.module.css'

export type PlanOp = { readonly system: string; readonly name: string; readonly size: number }

export type PlanSummary = {
  readonly send: readonly PlanOp[]
  readonly update: readonly PlanOp[]
  readonly remove: readonly PlanOp[]
  readonly unchanged: number
  /** Device folders that are not store systems, with how much each holds: named and left alone. */
  readonly unknownSystems: Readonly<Record<string, number>>
  readonly bytes: {
    readonly net: number
    readonly free: number | null
    readonly fits: boolean | null
  }
}

const total = (ops: readonly PlanOp[]) => formatBytes(ops.reduce((a, o) => a + o.size, 0))

/** What a sync will do, in one sentence, with the full list behind a toggle. */
export function PlanLine({ plan, list }: { plan: PlanSummary; list: ReactNode }) {
  const [shown, setShown] = useState(false)
  const listId = useId()
  const parts = (
    [
      ['send', plan.send],
      ['replace', plan.update],
      ['remove', plan.remove],
    ] as const
  ).filter(([, ops]) => ops.length > 0)
  const unknown = Object.entries(plan.unknownSystems)
  const b = plan.bytes
  return (
    <div className={styles.plan}>
      <p className={styles.line}>
        {parts.length === 0 ? (
          <Pill tone="ok">the device matches your selection</Pill>
        ) : (
          <>
            Sync will{' '}
            {parts.map(([verb, ops], i) => (
              <span key={verb}>
                {i > 0 && ', '}
                <b>
                  {verb} {ops.length.toLocaleString()}
                </b>{' '}
                ({total(ops)})
              </span>
            ))}
          </>
        )}{' '}
        · {plan.unchanged.toLocaleString()} already in place
      </p>
      <p className={styles.muted}>
        Net change {formatBytes(b.net)}
        {b.free != null && (
          <>
            {' '}
            · {formatBytes(b.free)} free now ·{' '}
            {b.fits ? <Pill tone="ok">fits</Pill> : <Pill tone="bad">does not fit</Pill>}
          </>
        )}
        . Games only, nothing wiped: Sync copies and removes the difference; bios and system files
        are never touched.{' '}
        {parts.length > 0 && (
          <ActionLink expanded={shown} controls={listId} onClick={() => setShown(!shown)}>
            {shown ? 'hide list' : 'show list'}
          </ActionLink>
        )}
      </p>
      {unknown.length > 0 && (
        <p className={styles.muted}>
          Folders on the device that are not store systems are left alone:{' '}
          {unknown.map(([s, n]) => `${s} (${n})`).join(', ')}
        </p>
      )}
      <div id={listId} hidden={!shown}>
        {shown && list}
      </div>
    </div>
  )
}
