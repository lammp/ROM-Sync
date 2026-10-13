import styles from './SegmentedControl.module.css'

export type Segment<V extends string> = { readonly value: V; readonly label: string }

export type SegmentedControlProps<V extends string> = {
  /** Names the group: "Rule for snes", "View". */
  readonly label: string
  readonly segments: readonly Segment<V>[]
  readonly value: V
  readonly onChange: (value: V) => void
  readonly disabled?: boolean
}

/** One choice among a few, as joined buttons: a radio group. */
export function SegmentedControl<V extends string>({
  label,
  segments,
  value,
  onChange,
  disabled,
}: SegmentedControlProps<V>) {
  return (
    <span className={styles.seg} role="radiogroup" aria-label={label}>
      {segments.map((s) => (
        <button
          key={s.value}
          type="button"
          role="radio"
          aria-checked={s.value === value}
          disabled={disabled}
          className={s.value === value ? styles.active : undefined}
          onClick={() => s.value !== value && onChange(s.value)}
        >
          {s.label}
        </button>
      ))}
    </span>
  )
}
