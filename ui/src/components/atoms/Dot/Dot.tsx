import styles from './Dot.module.css'

export type DotTone = 'neutral' | 'ok' | 'warn' | 'bad'

/**
 * A status dot. With a label it is an image named by the label; without one
 * it repeats what the text beside it says and is hidden from assistive
 * technology.
 */
export function Dot({ tone = 'neutral', label }: { tone?: DotTone; label?: string }) {
  const className = [styles.dot, tone !== 'neutral' && styles[tone]].filter(Boolean).join(' ')
  return label ? (
    <span role="img" aria-label={label} className={className} />
  ) : (
    <span aria-hidden="true" className={className} />
  )
}
