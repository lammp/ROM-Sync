import type { ReactNode } from 'react'
import styles from './ActionLink.module.css'

/** An action drawn as a link: "show 50 more", "clear". A button, so the keyboard reaches it. */
export function ActionLink({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" className={styles.link} onClick={onClick}>
      {children}
    </button>
  )
}
