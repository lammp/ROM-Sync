import { useId, type ReactNode } from 'react'
import { ActionLink } from '../../atoms/ActionLink/ActionLink'
import { Button } from '../../atoms/Button/Button'
import { Chevron } from '../../atoms/Chevron/Chevron'
import styles from './FacetSection.module.css'

export type FacetSectionProps = {
  readonly title: string
  /** Collapsed sections show only their heading. The state lives outside, so it persists. */
  readonly collapsed: boolean
  readonly onCollapsedChange: (collapsed: boolean) => void
  /** How many values are chosen; shown beside the title, and the clear control with it. */
  readonly chosen?: number
  readonly onClear?: () => void
  /** Values past the fold: "more" with the count, or "less" once unfolded. */
  readonly fold?: { readonly hidden: number; readonly less: boolean; readonly onToggle: () => void }
  /** The rows, composed by the organism above. */
  readonly children: ReactNode
}

/** One filter section of the sidebar: a disclosure heading, its rows, and the fold. */
export function FacetSection({
  title,
  collapsed,
  onCollapsedChange,
  chosen = 0,
  onClear,
  fold,
  children,
}: FacetSectionProps) {
  const body = useId()
  return (
    <section className={styles.facet} aria-label={title}>
      <h3 className={styles.heading}>
        <button
          type="button"
          className={styles.toggle}
          aria-expanded={!collapsed}
          aria-controls={body}
          onClick={() => onCollapsedChange(!collapsed)}
        >
          <Chevron collapsed={collapsed} />
          {title}
          {chosen > 0 && <span className={styles.count}>{chosen} chosen</span>}
        </button>
        {onClear && chosen > 0 && (
          <Button small onClick={onClear} aria-label={`Clear ${title}`}>
            clear
          </Button>
        )}
      </h3>
      <div id={body} className={styles.body} hidden={collapsed}>
        {children}
        {fold && fold.hidden > 0 && (
          <ActionLink onClick={fold.onToggle}>{`more… (+${fold.hidden})`}</ActionLink>
        )}
        {fold && fold.hidden === 0 && fold.less && (
          <ActionLink onClick={fold.onToggle}>less…</ActionLink>
        )}
      </div>
    </section>
  )
}
