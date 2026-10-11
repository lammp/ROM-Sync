import type { ReactNode } from 'react'
import { NavButton } from '../../atoms/NavButton/NavButton'
import styles from './AppHeader.module.css'

export type NavItem = { readonly href: string; readonly label: string; readonly current: boolean }

export type AppHeaderProps = {
  readonly nav: readonly NavItem[]
  readonly search: ReactNode
  readonly devicePicker: ReactNode
  readonly settings: NavItem
}

/** The header: the views, the search, the device in view, and settings. */
export function AppHeader({ nav, search, devicePicker, settings }: AppHeaderProps) {
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
      <NavButton href={settings.href} current={settings.current}>
        {settings.label}
      </NavButton>
    </>
  )
}
