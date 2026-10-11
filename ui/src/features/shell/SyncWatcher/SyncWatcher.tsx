'use client'

import { useEffect } from 'react'
import { formatBytes } from '../../../lib/format/format'
import { useProfiles } from '../../../queries/devices/devices'
import { TERMINAL } from '../../../queries/job/job'
import {
  sampleOf,
  useAfterDeviceJob,
  useSyncStatus,
  type SyncStatus,
} from '../../../queries/sync/sync'
import { appStore, useAppStore } from '../../../store/store'

/** What a finished sync did, in version 1's words; a failure is said as one. */
export function finishedText(name: string, status: SyncStatus): { text: string; bad: boolean } {
  const job = status.job
  if (!job) return { text: `${name}: the sync ended`, bad: false }
  if (job.state === 'failed')
    return {
      text: `Sync failed: ${job.error_message ?? job.error_code ?? 'unknown error'}`,
      bad: true,
    }
  const r = job.result ?? {}
  const failed = r.failed ?? 0
  const bits = [`sent ${(r.send ?? 0) + (r.update ?? 0)}`, `removed ${r.remove ?? 0}`]
  if (failed) bits.push(`${failed} failed`)
  const moved = status.run?.bytes_moved
  const what = `${bits.join(', ')}${moved != null ? ` (${formatBytes(moved)})` : ''}`
  if (job.state === 'cancelled')
    return { text: `${name}: sync cancelled after ${what}`, bad: false }
  return { text: `${name} synced: ${what}`, bad: failed > 0 }
}

/**
 * The sync in flight, watched from wherever the person is (F11-S32): each
 * poll advances the store's progress, and the end is said and read again.
 * Leaving the device's page does not stop it; version 1's poller did not
 * stop either.
 */
export function SyncWatcher() {
  const running = useAppStore((s) => s.sync.running)
  const profile = useProfiles().data?.find((p) => p.id === running?.device) ?? null
  const ref = running ? (profile?.ref ?? null) : null
  const status = useSyncStatus(ref, running !== null)
  const after = useAfterDeviceJob(running?.device ?? '', ref)
  const data = status.data

  useEffect(() => {
    const now = appStore.getState()
    const mine = now.sync.running
    if (!data?.job || !mine || data.job.id !== mine.job) return
    now.sync.poll(sampleOf(data), Date.now())
    if (!TERMINAL.has(data.job.state)) return
    now.sync.finish()
    const said = finishedText(profile?.name ?? 'Device', data)
    now.ui.toast(said.text, said.bad ? 'bad' : 'info')
    after()
  }, [data, profile, after])

  return null
}
