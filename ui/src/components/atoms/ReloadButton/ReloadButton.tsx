import { IconButton } from '../IconButton/IconButton'
import styles from './ReloadButton.module.css'

export type ReloadButtonProps = {
  /** What it reads again, as its name and tooltip: "Look for devices again". */
  readonly label: string
  /** It is reading now: the icon turns and the button waits. */
  readonly busy?: boolean
  readonly onClick: () => void
}

/** Read something again, drawn as the reload icon (F11-S49). */
export function ReloadButton({ label, busy = false, onClick }: ReloadButtonProps) {
  return (
    <IconButton label={label} disabled={busy} aria-busy={busy || undefined} onClick={onClick}>
      <svg
        className={busy ? `${styles.icon} ${styles.turning}` : styles.icon}
        viewBox="0 0 24 24"
        width="16"
        height="16"
        aria-hidden="true"
      >
        <path
          fill="currentColor"
          d="M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.73 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35Z"
        />
      </svg>
    </IconButton>
  )
}
