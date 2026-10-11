import styles from './SelectionBadge.module.css'

export type SelectionBadgeProps = {
  readonly selected: boolean
  /** Chosen by hand, against the system's rule; drawn dashed as well as coloured. */
  readonly override: boolean
  /** The game, for the badge's name. */
  readonly title: string
  readonly device: string
  readonly onToggle: () => void
}

/**
 * Whether a game goes to the device, and the control that changes it. An atom
 * by the placement rule: it renders no project component, and both GameTile
 * and GameRow carry it.
 */
export function SelectionBadge({
  selected,
  override,
  title,
  device,
  onToggle,
}: SelectionBadgeProps) {
  const state = `${selected ? 'selected' : 'not selected'}${override ? ', chosen by hand' : ''}`
  return (
    <button
      type="button"
      className={[styles.sel, selected && styles.in, override && styles.over]
        .filter(Boolean)
        .join(' ')}
      aria-pressed={selected}
      aria-label={`${title} for ${device}: ${state}`}
      title={`${selected ? 'In' : 'Not in'} the selection for ${device}${override ? ' (chosen by hand)' : ''}. Click to change.`}
      onClick={(e) => {
        e.stopPropagation()
        onToggle()
      }}
    >
      <span aria-hidden="true">{selected ? '✓' : ''}</span>
    </button>
  )
}
