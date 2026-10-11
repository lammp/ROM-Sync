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
