import { CoverImage } from '../../atoms/CoverImage/CoverImage'
import styles from './ScreenshotStrip.module.css'

export type Shot = { readonly thumb: string; readonly full: string }

/** The game's screenshots in a row; each opens at full size. */
export function ScreenshotStrip({
  shots,
  title,
  onOpen,
}: {
  shots: readonly Shot[]
  title: string
  onOpen: (shot: Shot) => void
}) {
  if (shots.length === 0) return null
  return (
    <ul className={styles.shots} aria-label={`Screenshots of ${title}`}>
      {shots.map((s, i) => (
        <li key={s.thumb}>
          <button type="button" className={styles.shot} onClick={() => onOpen(s)}>
            <CoverImage src={s.thumb} alt={`${title}, screenshot ${i + 1}`} size="row" />
          </button>
        </li>
      ))}
    </ul>
  )
}
