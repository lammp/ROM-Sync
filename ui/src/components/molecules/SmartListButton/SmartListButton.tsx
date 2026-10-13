import styles from './SmartListButton.module.css'

export type SmartListButtonProps = {
  readonly label: string
  /** The search it puts in the search box, shown as its description. */
  readonly query: string
  readonly onApply: (query: string) => void
}

/** A saved search: one click puts its query in the search box. */
export function SmartListButton({ label, query, onApply }: SmartListButtonProps) {
  return (
    <button type="button" className={styles.smart} title={query} onClick={() => onApply(query)}>
      {label}
    </button>
  )
}

/** Version 1's six smart lists. */
export const SMART_LISTS: readonly { readonly label: string; readonly query: string }[] = [
  { label: 'Top rated', query: 'rating>85 votes>50' },
  { label: 'Modern', query: 'year>2010' },
  { label: 'Retro', query: 'year<1995' },
  { label: 'Big games', query: 'size>1gb' },
  { label: 'RPGs', query: 'genre:rpg' },
  { label: 'Platformers', query: 'genre:platform' },
]
