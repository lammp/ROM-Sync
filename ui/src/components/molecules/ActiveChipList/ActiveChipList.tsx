import { ActionLink } from '../../atoms/ActionLink/ActionLink'
import { Chip } from '../../atoms/Chip/Chip'
import styles from './ActiveChipList.module.css'

export type ActiveFilter = {
  readonly key: string
  readonly label: string
  readonly onRemove: () => void
}

/** Every filter in force as a removable chip, and a way to clear them all. */
export function ActiveChipList({
  filters,
  onClearAll,
}: {
  filters: readonly ActiveFilter[]
  onClearAll: () => void
}) {
  if (filters.length === 0) return null
  return (
    <div className={styles.chips} role="group" aria-label="Filters in force">
      {filters.map((f) => (
        <Chip key={f.key} onRemove={f.onRemove} name={f.label}>
          {f.label}
        </Chip>
      ))}
      <ActionLink onClick={onClearAll}>clear all</ActionLink>
    </div>
  )
}
