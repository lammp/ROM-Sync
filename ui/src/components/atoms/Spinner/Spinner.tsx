import styles from './Spinner.module.css'

/** Work under way. Still, not spinning, when the reader asks for reduced motion. */
export function Spinner({ label = 'Working' }: { label?: string }) {
  return <span role="img" aria-label={label} className={styles.spin} />
}
