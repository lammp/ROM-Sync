import type { ButtonHTMLAttributes, ReactNode } from 'react'
import styles from './Button.module.css'

export type ButtonVariant = 'default' | 'primary' | 'danger'

export type ButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> & {
  readonly variant?: ButtonVariant
  /** A toggle that is on; announced as pressed. */
  readonly active?: boolean
  readonly small?: boolean
  readonly children: ReactNode
}

/** The one button. Primary fills with `--accent-solid` so its label passes 4.5:1. */
export function Button({
  variant = 'default',
  active,
  small = false,
  type = 'button',
  children,
  ...rest
}: ButtonProps) {
  const classes = [
    styles.button,
    variant !== 'default' && styles[variant],
    active && styles.active,
    small && styles.small,
  ]
  return (
    <button
      {...rest}
      type={type}
      aria-pressed={active === undefined ? undefined : active}
      className={classes.filter(Boolean).join(' ')}
    >
      {children}
    </button>
  )
}
