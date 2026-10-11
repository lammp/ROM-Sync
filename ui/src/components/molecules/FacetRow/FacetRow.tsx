import styles from './FacetRow.module.css'

export type FacetRowProps = {
  readonly label: string
  readonly count: number
  readonly chosen: boolean
  readonly onToggle: () => void
}

/**
 * One facet value and its count, a toggle button. A value with no games
 * left is muted rather than faded to 35 per cent, which fell below readable
 * contrast; its count of 0 says the same in words.
 */
export function FacetRow({ label, count, chosen, onToggle }: FacetRowProps) {
  return (
    <button
      type="button"
      aria-pressed={chosen}
      className={[styles.fact, chosen && styles.on, count === 0 && styles.zero]
        .filter(Boolean)
        .join(' ')}
      onClick={onToggle}
    >
      <span className={styles.label}>{label}</span>
      <span className={styles.n}>{count}</span>
    </button>
  )
}
