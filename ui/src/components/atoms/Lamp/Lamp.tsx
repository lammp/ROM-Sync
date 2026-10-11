import styles from './Lamp.module.css'

export type LampState = 'off' | 'on' | 'bad'

const NAMES: Readonly<Record<LampState, string>> = {
  off: 'Not connected',
  on: 'Connected',
  bad: 'Needs attention',
}

/**
 * A device's connection lamp. Unplugged is grey, never red: a handheld on the
 * desk is not an error, and red stays for a device in actual trouble.
 */
export function Lamp({ state, label }: { state: LampState; label?: string }) {
  return (
    <span
      role="img"
      aria-label={label ?? NAMES[state]}
      className={[styles.lamp, state !== 'off' && styles[state]].filter(Boolean).join(' ')}
    />
  )
}
