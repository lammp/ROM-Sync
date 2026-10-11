import { formatBytes } from '../../../lib/format/format'
import { Pill } from '../../atoms/Pill/Pill'
import styles from './PlanDetailList.module.css'

export type PlanItem = {
  readonly action: 'send' | 'update' | 'remove'
  readonly system: string
  readonly name: string
  readonly size: number
}

const VERB = { send: 'send', update: 'replace', remove: 'remove' } as const

/** Every operation the sync will make, in order. */
export function PlanDetailList({ items }: { items: readonly PlanItem[] }) {
  return (
    <ul className={styles.list} aria-label="Everything the sync will do">
      {items.map((o) => (
        <li key={`${o.action}:${o.system}\\${o.name}`}>
          <Pill tone={o.action === 'remove' ? 'warn' : 'neutral'}>{VERB[o.action]}</Pill> {o.system}{' '}
          \ {o.name} <span className={styles.muted}>{formatBytes(o.size)}</span>
        </li>
      ))}
    </ul>
  )
}
