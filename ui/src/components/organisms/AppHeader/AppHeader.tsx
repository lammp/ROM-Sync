import type { ReactNode } from 'react'
import { NavButton } from '../../atoms/NavButton/NavButton'
import styles from './AppHeader.module.css'

export type NavItem = { readonly href: string; readonly label: string; readonly current: boolean }

export type AppHeaderProps = {
  readonly nav: readonly NavItem[]
  readonly search: ReactNode
  readonly devicePicker: ReactNode
  readonly settings: NavItem
  /** The notification bell, beside settings. */
  readonly notices?: ReactNode
}

/** The header: the views, the search, the device in view, the notifications, and settings as a cog. */
export function AppHeader({ nav, search, devicePicker, settings, notices }: AppHeaderProps) {
  return (
    <>
      <span className={styles.brand}>ROM-Sync</span>
      <nav className={styles.nav} aria-label="Main">
        {nav.map((n) => (
          <NavButton key={n.href} href={n.href} current={n.current}>
            {n.label}
          </NavButton>
        ))}
      </nav>
      <div className={styles.search}>{search}</div>
      <div className={styles.device}>{devicePicker}</div>
      {notices}
      <NavButton href={settings.href} current={settings.current} label={settings.label}>
        <svg className={styles.cog} viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path
            fill="currentColor"
            d="M19.4 13a7.5 7.5 0 0 0 0-2l2.1-1.6a.5.5 0 0 0 .1-.6l-2-3.5a.5.5 0 0 0-.6-.2l-2.5 1a7.4 7.4 0 0 0-1.7-1L14.4 2.4A.5.5 0 0 0 14 2h-4a.5.5 0 0 0-.5.4l-.4 2.7a7.4 7.4 0 0 0-1.7 1l-2.5-1a.5.5 0 0 0-.6.2l-2 3.5a.5.5 0 0 0 .1.6L4.6 11a7.5 7.5 0 0 0 0 2l-2.1 1.6a.5.5 0 0 0-.1.6l2 3.5a.5.5 0 0 0 .6.2l2.5-1a7.4 7.4 0 0 0 1.7 1l.4 2.7a.5.5 0 0 0 .5.4h4a.5.5 0 0 0 .5-.4l.4-2.7a7.4 7.4 0 0 0 1.7-1l2.5 1a.5.5 0 0 0 .6-.2l2-3.5a.5.5 0 0 0-.1-.6L19.4 13ZM12 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7Z"
          />
        </svg>
      </NavButton>
    </>
  )
}
