import { Button } from '../../atoms/Button/Button'
import { Chip, type ChipKind } from '../../atoms/Chip/Chip'
import styles from './TagChipGroup.module.css'

export type Tag = {
  readonly tag: string
  readonly kind: string
  readonly state: 'accepted' | 'proposed'
}

export type TagChipGroupProps = {
  readonly genres: readonly string[]
  readonly tags: readonly Tag[]
  /** Removes an accepted tag; the decision stands against later passes. */
  readonly onRemove: (tag: Tag) => void
  /** Accepts or rejects a suggested tag. */
  readonly onDecide: (tag: Tag, accept: boolean) => void
}

const KINDS: ReadonlySet<string> = new Set([
  'franchise',
  'collection',
  'theme',
  'mode',
  'perspective',
])
const kindOf = (t: Tag): ChipKind =>
  t.state === 'proposed' ? 'suggested' : KINDS.has(t.kind) ? (t.kind as ChipKind) : 'plain'

/** A game's genres and tags; suggested tags wait for a decision. */
export function TagChipGroup({ genres, tags, onRemove, onDecide }: TagChipGroupProps) {
  return (
    <div className={styles.chips} role="group" aria-label="Genres and tags">
      {genres.map((g) => (
        <Chip key={`genre:${g}`}>{g}</Chip>
      ))}
      {tags.map((t) =>
        t.state === 'proposed' ? (
          <Chip key={`${t.kind}:${t.tag}`} kind="suggested">
            <span title={`${t.kind}, suggested`}>{t.tag}</span>
            <span className={styles.decide}>
              <Button small aria-label={`Accept ${t.tag}`} onClick={() => onDecide(t, true)}>
                ✓
              </Button>
              <Button small aria-label={`Reject ${t.tag}`} onClick={() => onDecide(t, false)}>
                ✗
              </Button>
            </span>
          </Chip>
        ) : (
          <Chip
            key={`${t.kind}:${t.tag}`}
            kind={kindOf(t)}
            name={t.tag}
            onRemove={() => onRemove(t)}
          >
            <span title={t.kind}>{t.tag}</span>
          </Chip>
        ),
      )}
    </div>
  )
}
