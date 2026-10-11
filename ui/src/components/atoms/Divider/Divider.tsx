import styles from './Divider.module.css'

/** A decorative rule between sections; 1.4.11 exempts it, so it keeps the quiet `--divider`. */
export function Divider() {
  return <hr className={styles.divider} />
}
