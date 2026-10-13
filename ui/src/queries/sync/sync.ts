/**
 * A device's sync (F10-S12, S25): its status read while one runs, starting
 * one with the removals the person saw, and cancelling it. The engine plans
 * again at the start and refuses a plan that changed under the person.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import type { components } from '../../lib/api/api'
import type { Sample } from '../../lib/progress/progress'
import { TERMINAL } from '../job/job'
import { unwrap, useEngine } from '../engine/engine'

export type SyncStatus = components['schemas']['SyncStatusView']

const num = (v: unknown) => (typeof v === 'number' ? v : undefined)

/**
 * One poll as lib/progress reads it: the run, the bytes sent and removed so
 * far, and the run's phase, item and counts. The engine's job progress
 * carries the totals (F10-S25); a run that has ended has only its record.
 */
export function sampleOf(status: SyncStatus): Sample {
  const { job, run } = status
  const d = job?.progress?.detail ?? {}
  const counts = run?.counts ?? {}
  const running = job !== null && job !== undefined && !TERMINAL.has(job.state)
  return {
    run: run ? String(run.id) : null,
    bytes_done: running ? (num(d.bytes_done) ?? 0) : (run?.bytes_moved ?? num(d.bytes_done) ?? 0),
    bytes_removed: num(d.bytes_removed) ?? 0,
    status: {
      state: running ? 'running' : (run?.state ?? job?.state),
      phase: job?.progress?.phase,
      current: job?.progress?.current ?? undefined,
      sent: num(d.sent) ?? num(counts.send),
      removed: num(d.removed) ?? num(counts.remove),
      failed: num(counts.failed),
    },
  }
}

/** The device's sync, asked again at the engine's poll interval while `watching`. */
export function useSyncStatus(ref: string | null, watching: boolean) {
  const { api, pollMs } = useEngine()
  return useQuery({
    queryKey: ['sync', ref ?? ''],
    enabled: ref !== null,
    queryFn: async ({ signal }) =>
      unwrap(
        await api.GET('/api/v1/devices/{ref}/sync', {
          params: { path: { ref: ref ?? '' } },
          signal,
        }),
      ),
    refetchInterval: watching ? pollMs : false,
  })
}

/** Starts the sync, confirming the removals the person was shown. */
export function useStartSync(ref: string) {
  const { api } = useEngine()
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (confirmRemovals: number | null) =>
      unwrap(
        await api.POST('/api/v1/devices/{ref}/sync', {
          params: { path: { ref } },
          body: { confirm_removals: confirmRemovals },
        }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: ['sync', ref] }),
  })
}

export function useCancelSync(ref: string) {
  const { api } = useEngine()
  const client = useQueryClient()
  return useMutation({
    mutationFn: async () =>
      unwrap(await api.POST('/api/v1/devices/{ref}/sync/cancel', { params: { path: { ref } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: ['sync', ref] }),
  })
}

/**
 * After a job on the device ends (a sync, a scan, a marker written), what it
 * may have changed is read again: contents, runs, selection, profiles, plan
 * and space.
 */
export function useAfterDeviceJob(deviceId: string, ref: string | null) {
  const client = useQueryClient()
  return useCallback(() => {
    const keys: (readonly string[])[] = [
      ['inventory', deviceId],
      ['runs', deviceId],
      ['selection', deviceId],
      ['profiles'],
    ]
    if (ref !== null) keys.push(['plan', ref], ['capacity', ref], ['sync', ref])
    for (const queryKey of keys) void client.invalidateQueries({ queryKey })
  }, [client, deviceId, ref])
}
