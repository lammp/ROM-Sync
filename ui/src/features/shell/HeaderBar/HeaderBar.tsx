'use client'

import { usePathname, useRouter } from 'next/navigation'
import { SearchInput } from '../../../components/atoms/SearchInput/SearchInput'
import { AppHeader } from '../../../components/organisms/AppHeader/AppHeader'
import { DevicePicker } from '../../../components/organisms/DevicePicker/DevicePicker'
import { NotificationCentre } from '../../../components/organisms/NotificationCentre/NotificationCentre'
import { attachedFor, useAttached, useProfiles } from '../../../queries/devices/devices'
import { useRecoverLists } from '../../../queries/recover/recover'
import { appStore, useAppStore } from '../../../store/store'

const VIEWS = [
  { href: '/', label: 'Library' },
  { href: '/devices', label: 'Devices' },
  { href: '/system-files', label: 'System files' },
] as const

/** Shown only while a device plugged in holds something the store does not (REBUILD-UI section 11). */
const RECOVER = { href: '/recover', label: 'Recover' } as const

/** A route's path without the trailing slash the static export adds. */
export function routeOf(pathname: string | null): string {
  const p = (pathname ?? '/').replace(/\/+$/, '')
  return p === '' ? '/' : p
}

/** The header, bound: the current view, the library search, and the device in view. */
export function HeaderBar() {
  const route = routeOf(usePathname())
  const router = useRouter()
  const query = useAppStore((s) => s.filters.query)
  const device = useAppStore((s) => s.selection.device)
  const profiles = useProfiles().data ?? []
  const attached = useAttached().data?.devices ?? []
  const lists = useRecoverLists(attached.filter((d) => d.profile !== null).map((d) => d.ref))
  const recover = lists.some((l) => (l.data?.length ?? 0) > 0)
  const views = recover || route === RECOVER.href ? [...VIEWS, RECOVER] : VIEWS
  const notices = useAppStore((s) => s.ui.notices)
  return (
    <AppHeader
      nav={views.map((v) => ({ ...v, current: route === v.href }))}
      search={
        <SearchInput
          value={query}
          onChange={(q) => {
            appStore.getState().filters.setQuery(q)
            if (route !== '/') router.push('/')
          }}
        />
      }
      devicePicker={
        <DevicePicker
          devices={profiles.map((p) => ({
            id: p.id,
            name: p.name,
            online: attachedFor(attached, p.id) !== null,
          }))}
          value={device}
          onChange={(id) => appStore.getState().selection.choose(id)}
        />
      }
      notices={
        <NotificationCentre
          notices={notices}
          onOpen={() => appStore.getState().ui.readNotices()}
          onClear={(id) => appStore.getState().ui.clearNotice(id)}
          onClearAll={() => appStore.getState().ui.clearNotices()}
          onFollow={(href) => {
            const [path, hash] = href.split('#')
            // a tab of the page already open: the address's hash changes, and the page follows it
            if (hash && routeOf(path ?? '/') === route) window.location.hash = hash
            else router.push(href)
          }}
        />
      }
      settings={{ href: '/settings', label: 'Settings', current: route === '/settings' }}
    />
  )
}
