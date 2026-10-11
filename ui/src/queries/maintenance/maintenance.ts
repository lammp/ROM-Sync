/**
 * The data folder's upkeep (F10-S14): each action's dry run, and running it
 * with the count that dry run found, so a change in between refuses it.
 */
import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query'
import type { components } from '../../lib/api/api'
import { unwrap, useEngine } from '../engine/engine'

export type Report = components['schemas']['MaintenanceReport']

export const ACTIONS = ['compact', 'clear-cache', 'prune-covers', 'prune-runs'] as const
export type Action = (typeof ACTIONS)[number]

/** Every action's dry run, in order. */
export function useMaintenanceReports() {
  const { api } = useEngine()
  return useQueries({
    queries: ACTIONS.map((action) => ({
      queryKey: ['maintenance', action],
      queryFn: async ({ signal }: { signal: AbortSignal }) =>
        unwrap(
          await api.GET('/api/v1/maintenance/{action}', { params: { path: { action } }, signal }),
        ),
    })),
  })
}

/** Runs an action with the count its dry run found; every dry run is read again after. */
export function useRunMaintenance() {
  const { api } = useEngine()
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (run: { action: Action; expected: number }) =>
      unwrap(
        await api.POST('/api/v1/maintenance/{action}', {
          params: { path: { action: run.action } },
          body: { expected: run.expected },
        }),
      ),
    onSettled: () => client.invalidateQueries({ queryKey: ['maintenance'] }),
  })
}
