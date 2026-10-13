/**
 * A job, polled while it runs (F11-S7).
 *
 * The poll stops by itself when the job reaches a terminal state, and stops
 * with the page: unmounting the last observer cancels the request in flight
 * through its abort signal and no further poll is scheduled. Version 1's
 * `SYNC`, `CAP` and `DEVWATCH` timers outlived their pages; this cannot.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { components } from '../../lib/api/api'
import { unwrap, useEngine } from '../engine/engine'

export type Job = components['schemas']['JobView']

export const TERMINAL: ReadonlySet<string> = new Set(['done', 'failed', 'cancelled'])

export function jobKey(id: string) {
  return ['job', id] as const
}

/** Whether a job has stopped and will not change again. */
export function finished(job: Job | undefined): boolean {
  return job !== undefined && TERMINAL.has(job.state)
}

export function useJob(id: string | null) {
  const { api, pollMs } = useEngine()
  return useQuery({
    queryKey: jobKey(id ?? ''),
    enabled: id !== null,
    queryFn: async ({ signal }) =>
      unwrap(
        await api.GET('/api/v1/jobs/{job_id}', { params: { path: { job_id: id ?? '' } }, signal }),
      ),
    refetchInterval: (query) => (finished(query.state.data) ? false : pollMs),
  })
}

export function useCancelJob() {
  const { api } = useEngine()
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) =>
      unwrap(await api.POST('/api/v1/jobs/{job_id}/cancel', { params: { path: { job_id: id } } })),
    onSuccess: (job) => client.setQueryData(jobKey(job.id), job),
  })
}

/** Every job the engine holds, asked again at the poll interval while any runs. */
export function useJobs() {
  const { api, pollMs } = useEngine()
  return useQuery({
    queryKey: ['jobs'],
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/v1/jobs', { signal })).jobs,
    refetchInterval: (query) =>
      (query.state.data ?? []).some((j) => !TERMINAL.has(j.state)) ? pollMs : false,
  })
}

/**
 * Every job the engine holds, read on a steady beat whether or not one is
 * running, so a job that ends anywhere is noticed (F11-S47): one started on
 * another page, before this page loaded, or by the engine on its own.
 */
export function useJobFeed() {
  const { api, pollMs } = useEngine()
  return useQuery({
    queryKey: ['jobs', 'feed'],
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/v1/jobs', { signal })).jobs,
    refetchInterval: pollMs * FEED_BEATS,
  })
}

/** The feed is read once every this many job polls: every five seconds in the application. */
export const FEED_BEATS = 5
