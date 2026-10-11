import styles from './Chevron.module.css'

/** The facet disclosure mark; it turns when collapsed. Its control says the state, so it is hidden. */
export function Chevron({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={[styles.chev, collapsed && styles.collapsed].filter(Boolean).join(' ')}
    />
  )
}
