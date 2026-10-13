import Link from 'next/link'
import type { ReactNode } from 'react'
import styles from './TextLink.module.css'

export type TextLinkProps = {
  readonly href: string
  readonly children: ReactNode
  /** A page outside the application: opened apart, never with a referrer. */
  readonly external?: boolean
}

/** A link in running text, to a route or to the web. */
export function TextLink({ href, children, external = false }: TextLinkProps) {
  return external ? (
    <a href={href} className={styles.link} target="_blank" rel="noreferrer noopener">
      {children}
    </a>
  ) : (
    <Link href={href} className={styles.link}>
      {children}
    </Link>
  )
}
