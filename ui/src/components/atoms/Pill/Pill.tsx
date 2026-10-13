import type { ReactNode } from 'react'
import styles from './Pill.module.css'

export type Tone = 'neutral' | 'ok' | 'warn' | 'bad'

/** A short status label: a job's state, a match's confidence. */
export function Pill({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={[styles.pill, tone !== 'neutral' && styles[tone]].filter(Boolean).join(' ')}>
      {children}
    </span>
  )
}
