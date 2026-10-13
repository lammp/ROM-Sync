import Link from 'next/link'
import type { ReactNode } from 'react'
import styles from './NavButton.module.css'

export type NavButtonProps = {
  readonly href: string
  /** The route this link names is the one on screen. */
  readonly current?: boolean
  /** The link's name when its content is an icon alone; also its tooltip. */
  readonly label?: string
  readonly children: ReactNode
}

/** A header navigation entry: a real link, since every view is a route. */
export function NavButton({ href, current = false, label, children }: NavButtonProps) {
  return (
    <Link
      href={href}
      aria-current={current ? 'page' : undefined}
      aria-label={label}
      title={label}
      className={[styles.nav, current && styles.current].filter(Boolean).join(' ')}
    >
      {children}
    </Link>
  )
}
