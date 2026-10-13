import type { ReactNode } from 'react'
import { Icon, type IconName } from '../Icon/Icon'
import styles from './LinkButton.module.css'

export type LinkButtonProps = {
  readonly href: string
  /** The file name to save what it fetches as. */
  readonly download: string
  readonly icon?: IconName
  readonly large?: boolean
  readonly children: ReactNode
}

/**
 * A download drawn as a button (F11-S51): it is a link, because it fetches a
 * file rather than changing anything, but it is a tab's main action, so it
 * looks like one.
 */
export function LinkButton({
  href,
  download,
  icon = 'download',
  large = false,
  children,
}: LinkButtonProps) {
  return (
    <a
      href={href}
      download={download}
      className={[styles.link, large && styles.large].filter(Boolean).join(' ')}
    >
      <Icon name={icon} />
      {children}
    </a>
  )
}
