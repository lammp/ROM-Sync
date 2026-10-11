import Link from 'next/link'
import type { ReactNode } from 'react'
import styles from './NavButton.module.css'

export type NavButtonProps = {
  readonly href: string
  /** The route this link names is the one on screen. */
  readonly current?: boolean
  readonly children: ReactNode
}

/** A header navigation entry: a real link, since every view is a route. */
export function NavButton({ href, current = false, children }: NavButtonProps) {
  return (
    <Link
      href={href}
      aria-current={current ? 'page' : undefined}
      className={[styles.nav, current && styles.current].filter(Boolean).join(' ')}
    >
      {children}
    </Link>
  )
}
