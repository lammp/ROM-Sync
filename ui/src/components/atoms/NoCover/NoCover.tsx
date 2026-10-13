import styles from './NoCover.module.css'

/** The placeholder for a game without cover art: its title on a gradient. */
export function NoCover({ title }: { title: string }) {
  return <div className={styles.nocov}>{title}</div>
}
