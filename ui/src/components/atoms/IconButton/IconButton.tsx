import type { ButtonHTMLAttributes, ReactNode } from 'react'
import styles from './IconButton.module.css'

export type IconButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  'className' | 'aria-label' | 'children'
> & {
  /** The accessible name; an icon alone has none. */
  readonly label: string
  readonly active?: boolean
  /** A decorative icon; it is hidden from assistive technology. */
  readonly children: ReactNode
}

/** A button drawn as an icon: the settings cog, the detail panel's close. */
export function IconButton({
  label,
  active = false,
  children,
  type = 'button',
  ...rest
}: IconButtonProps) {
  return (
    <button
      {...rest}
      type={type}
      aria-label={label}
      title={label}
      className={[styles.icon, active && styles.active].filter(Boolean).join(' ')}
    >
      <span aria-hidden="true" className={styles.glyph}>
        {children}
      </span>
    </button>
  )
}
