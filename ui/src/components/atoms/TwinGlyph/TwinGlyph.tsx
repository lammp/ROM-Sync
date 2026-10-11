import styles from './TwinGlyph.module.css'

export type TwinGlyphProps = {
  /** The same game is in the library more than once on one system. */
  readonly dupe?: boolean
  readonly label: string
}

/** The ⇄ corner mark: this game exists on other systems, or twice here. */
export function TwinGlyph({ dupe = false, label }: TwinGlyphProps) {
  return (
    <span
      role="img"
      aria-label={label}
      className={[styles.twin, dupe && styles.dupe].filter(Boolean).join(' ')}
    >
      <span aria-hidden="true">⇄</span>
    </span>
  )
}
