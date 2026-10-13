'use client'

import { useEffect, useRef } from 'react'
import { deviceNotice, jobNotice, setupNotices } from '../../../lib/notices/notices'
import { useAttached, useProfiles } from '../../../queries/devices/devices'
import { useJobFeed } from '../../../queries/job/job'
import { useSystems } from '../../../queries/library/library'
import { useAnnounce } from '../../../queries/meta/meta'
import { useSettings } from '../../../queries/settings/settings'
import { appStore } from '../../../store/store'

/**
 * Turns what happens into notifications (F11-S47), from wherever the person
 * is. A job that ends is said by its kind; one that ended before the page
 * loaded is added to the list without a toast. A device seen to connect or
 * disconnect is said. The setup steps still to do are listed, and taken away
 * once done.
 */
export function NoticeWatcher() {
  const jobs = useJobFeed().data
  const profiles = useProfiles().data
  const attached = useAttached()
  const settings = useSettings().data
  const systems = useSystems().data
  const announce = useAnnounce()
  const since = useRef<number | null>(null)
  const online = useRef<Map<string, string> | null>(null)
  const transitions = useRef(0)

  useEffect(() => {
    since.current ??= Date.now()
  }, [])

  useEffect(() => {
    if (!jobs || since.current === null) return
    const name = (ref: string | null) =>
      profiles?.find((p) => p.ref === ref || p.id === ref)?.name ?? undefined
    for (const job of [...jobs].reverse()) {
      const notice = jobNotice(job, name(job.target))
      if (!notice) continue
      const at = job.finished ? Date.parse(job.finished) : Date.now()
      const fresh = !Number.isNaN(at) && at >= since.current - 1000
      if (fresh) announce(job, notice)
      else appStore.getState().ui.notify({ ...notice, at: Number.isNaN(at) ? Date.now() : at })
    }
  }, [jobs, profiles, announce])

  useEffect(() => {
    if (!attached.isSuccess) return
    // keyed by profile: the same device back over another transport is not a new one (F11-S53)
    const now = new Map(
      attached.data.devices.flatMap((d) =>
        d.profile ? [[d.profile.id, d.profile.name] as const] : [],
      ),
    )
    const before = online.current
    online.current = now
    if (before === null) return
    const changes = [
      ...[...now].filter(([ref]) => !before.has(ref)).map(([ref, n]) => [ref, n, true] as const),
      ...[...before].filter(([ref]) => !now.has(ref)).map(([ref, n]) => [ref, n, false] as const),
    ]
    for (const [ref, n, connected] of changes) {
      transitions.current += 1
      const notice = deviceNotice(ref, n, connected, Date.now() + transitions.current)
      if (appStore.getState().ui.notify({ ...notice, at: Date.now() }))
        appStore.getState().ui.toast(notice.title)
    }
  }, [attached.isSuccess, attached.data])

  useEffect(() => {
    if (!settings || !systems) return
    const value = (key: string) => settings.find((s) => s.key === key)
    const wanted = setupNotices({
      storeSet: Boolean(value('store.root')?.value),
      systems: systems.length,
      credentials:
        Boolean(value('igdb.client_id')?.value) &&
        Boolean(value('igdb.client_secret')?.secret_state?.present),
    })
    const ui = appStore.getState().ui
    for (const n of wanted) ui.notify({ ...n, at: Date.now() })
    const ids = new Set(wanted.map((n) => n.id))
    for (const n of ui.notices)
      if (n.source === 'setup' && !ids.has(n.id)) appStore.getState().ui.retract(n.id)
  }, [settings, systems])

  return null
}
