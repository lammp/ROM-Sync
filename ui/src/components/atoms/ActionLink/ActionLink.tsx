import type { ReactNode } from 'react'
import styles from './ActionLink.module.css'

/** An action drawn as a link: "show 50 more", "clear". A button, so the keyboard reaches it. */
export function ActionLink({
  onClick,
  children,
  expanded,
  controls,
}: {
  onClick: () => void
  children: ReactNode
  /** For a link that shows and hides something: whether it is shown, and its id. */
  expanded?: boolean
  controls?: string
}) {
  return (
    <button
      type="button"
      className={styles.link}
      aria-expanded={expanded}
      aria-controls={controls}
      onClick={onClick}
    >
      {children}
    </button>
  )
}
