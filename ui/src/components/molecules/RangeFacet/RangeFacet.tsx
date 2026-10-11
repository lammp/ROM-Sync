import { useId, useState } from 'react'
import { TextInput } from '../../atoms/TextInput/TextInput'
import styles from './RangeFacet.module.css'

export type Pair = { readonly lo: number; readonly hi: number }

/**
 * Moves one thumb, held so the two never cross and stay `gap` steps apart:
 * ten for size, none for year, as version 1 held them.
 */
export function movePair(pair: Pair, thumb: 'lo' | 'hi', to: number, gap: number): Pair {
  return thumb === 'lo'
    ? { lo: Math.min(to, pair.hi - gap), hi: pair.hi }
    : { lo: pair.lo, hi: Math.max(to, pair.lo + gap) }
}

type Exact = {
  /** The bound as typed text: a formatted size, a year, or empty for no limit. */
  readonly min: string
  readonly max: string
  readonly onMin: (text: string) => void
  readonly onMax: (text: string) => void
  readonly minPlaceholder: string
  readonly maxPlaceholder: string
}

export type RangeFacetProps = {
  readonly title: string
  readonly min: number
  readonly max: number
  readonly value: Pair
  readonly gap: number
  readonly onChange: (pair: Pair) => void
  /** What a thumb's position means, announced in place of the number. */
  readonly valueText: (position: number) => string
  readonly exact: Exact
}

/** A typed bound, kept as a draft while edited and committed on Enter or on leaving the field. */
function ExactField({
  label,
  committed,
  placeholder,
  onCommit,
}: {
  label: string
  committed: string
  placeholder: string
  onCommit: (text: string) => void
}) {
  const [draft, setDraft] = useState(committed)
  return (
    <span
      className={styles.exactField}
      onBlur={() => draft !== committed && onCommit(draft)}
      onKeyDown={(e) => e.key === 'Enter' && onCommit(draft)}
    >
      <TextInput
        label={label}
        hideLabel
        value={draft}
        placeholder={placeholder}
        onChange={setDraft}
      />
    </span>
  )
}

/** Paired sliders over one scale, with typed bounds beneath: the size and year facets. */
export function RangeFacet({
  title,
  min,
  max,
  value,
  gap,
  onChange,
  valueText,
  exact,
}: RangeFacetProps) {
  const heading = useId()
  const thumb = (which: 'lo' | 'hi') => (
    <input
      type="range"
      className={styles.thumb}
      min={min}
      max={max}
      value={value[which]}
      aria-label={which === 'lo' ? `${title}, lower bound` : `${title}, upper bound`}
      aria-valuetext={valueText(value[which])}
      onChange={(e) => onChange(movePair(value, which, Number(e.target.value), gap))}
    />
  )
  return (
    <section className={styles.facet} aria-labelledby={heading}>
      <h3 id={heading} className={styles.heading}>
        {title}
      </h3>
      <div className={styles.slider2}>
        {thumb('lo')}
        {thumb('hi')}
      </div>
      <div className={styles.exact}>
        <ExactField
          key={`min:${exact.min}`}
          label={`${title}, from`}
          committed={exact.min}
          placeholder={exact.minPlaceholder}
          onCommit={exact.onMin}
        />
        <span aria-hidden="true">–</span>
        <ExactField
          key={`max:${exact.max}`}
          label={`${title}, to`}
          committed={exact.max}
          placeholder={exact.maxPlaceholder}
          onCommit={exact.onMax}
        />
      </div>
    </section>
  )
}
