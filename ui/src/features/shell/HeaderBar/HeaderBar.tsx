'use client'

import { usePathname, useRouter } from 'next/navigation'
import { SearchInput } from '../../../components/atoms/SearchInput/SearchInput'
import { AppHeader } from '../../../components/organisms/AppHeader/AppHeader'
import { DevicePicker } from '../../../components/organisms/DevicePicker/DevicePicker'
import { useAttached, useProfiles } from '../../../queries/devices/devices'
import { appStore, useAppStore } from '../../../store/store'

const VIEWS = [
  { href: '/', label: 'Library' },
  { href: '/devices', label: 'Devices' },
  { href: '/system-files', label: 'System files' },
] as const

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
  const online = new Set((useAttached().data?.devices ?? []).map((d) => d.ref))
  return (
    <AppHeader
      nav={VIEWS.map((v) => ({ ...v, current: route === v.href }))}
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
            online: p.ref !== null && online.has(p.ref),
          }))}
          value={device}
          onChange={(id) => appStore.getState().selection.choose(id)}
        />
      }
      settings={{ href: '/settings', label: 'Settings', current: route === '/settings' }}
    />
  )
}
