import { Pill } from '../../atoms/Pill/Pill'
import styles from './TransportList.module.css'

export type Transport = {
  readonly kind: string
  readonly available: boolean
  readonly detail: string
}

const NAMES: Readonly<Record<string, string>> = { volume: 'Drives', mtp: 'MTP', adb: 'ADB' }

/**
 * Detected transports (F13-S8, SETTINGS.md section 4): each one the last probe
 * asked or could not, and in words what it said. A transport turned off or
 * without its tool is a state, so it reads as one: a word, not an error.
 */
export function TransportList({ transports }: { transports: readonly Transport[] }) {
  if (transports.length === 0) return null
  return (
    <ul className={styles.list} aria-label="Detected transports">
      {transports.map((t) => (
        <li key={t.kind} className={styles.item}>
          <b>{NAMES[t.kind] ?? t.kind}</b>
          <Pill tone={t.available ? 'ok' : 'warn'}>
            {t.available ? 'available' : 'not available'}
          </Pill>
          <span className={styles.detail}>{t.detail}</span>
        </li>
      ))}
    </ul>
  )
}
