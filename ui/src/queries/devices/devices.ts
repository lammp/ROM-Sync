/**
 * Devices (F10-S10, S11, S22): what is attached, the profiles, and for one
 * profile its selection, its inventory, its plan and its capacity; and the
 * selection changes, each answered by the engine's own rule.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import type { components } from '../../lib/api/api'
import { unwrap, useEngine } from '../engine/engine'

export type Profile = components['schemas']['Profile']
export type Attached = components['schemas']['AttachedDevice']
export type SelectionView = components['schemas']['SelectionView']
export type PlanView = components['schemas']['PlanView']

/** How often attached devices are asked for, in milliseconds: version 1's probe interval. */
export const PROBE_MS = 15_000

export function useAttached() {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['devices'],
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/v1/devices', { signal })),
    refetchInterval: PROBE_MS,
  })
}

export function useProfiles() {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['profiles'],
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/v1/profiles', { signal })).profiles,
  })
}

export function useSelection(deviceId: string | null) {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['selection', deviceId ?? ''],
    enabled: deviceId !== null,
    queryFn: async ({ signal }) =>
      unwrap(
        await api.GET('/api/v1/profiles/{device_id}/selection', {
          params: { path: { device_id: deviceId ?? '' } },
          signal,
        }),
      ),
  })
}

export function useInventory(deviceId: string | null) {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['inventory', deviceId ?? ''],
    enabled: deviceId !== null,
    queryFn: async ({ signal }) =>
      unwrap(
        await api.GET('/api/v1/profiles/{device_id}/inventory', {
          params: { path: { device_id: deviceId ?? '' } },
          signal,
        }),
      ).items,
  })
}

export function usePlan(ref: string | null) {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['plan', ref ?? ''],
    enabled: ref !== null,
    queryFn: async ({ signal }) =>
      unwrap(
        await api.GET('/api/v1/devices/{ref}/plan', {
          params: { path: { ref: ref ?? '' } },
          signal,
        }),
      ),
  })
}

export function useCapacity(ref: string | null) {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['capacity', ref ?? ''],
    enabled: ref !== null,
    queryFn: async ({ signal }) =>
      unwrap(
        await api.GET('/api/v1/devices/{ref}/capacity', {
          params: { path: { ref: ref ?? '' } },
          signal,
        }),
      ),
  })
}

/**
 * A selection change answers with the selection, which replaces the one held.
 * The plan and the space it needs are not read on every change: the selection
 * summary waits for changes to settle (F11-S28) and then calls the refresh.
 */
function useAfterSelection(deviceId: string) {
  const client = useQueryClient()
  return (selection: SelectionView) => client.setQueryData(['selection', deviceId], selection)
}

/** Reads the plan and the device's space again, for the summary's settled call. */
export function useRefreshCapacity(ref: string | null) {
  const client = useQueryClient()
  return useCallback(() => {
    if (ref === null) return
    void client.invalidateQueries({ queryKey: ['plan', ref] })
    void client.invalidateQueries({ queryKey: ['capacity', ref] })
  }, [client, ref])
}

export function useSetGames(deviceId: string) {
  const { api } = useEngine()
  const after = useAfterSelection(deviceId)
  return useMutation({
    mutationFn: async (change: { gameIds: readonly number[]; include: boolean }) =>
      unwrap(
        await api.POST('/api/v1/profiles/{device_id}/selection/games', {
          params: { path: { device_id: deviceId } },
          body: { game_ids: [...change.gameIds], include: change.include },
        }),
      ),
    onSuccess: (r) => after(r.selection),
  })
}

export function useSetMode(deviceId: string) {
  const { api } = useEngine()
  const after = useAfterSelection(deviceId)
  return useMutation({
    mutationFn: async (change: { system: string; mode: 'all' | 'none' | 'off' }) =>
      unwrap(
        await api.POST('/api/v1/profiles/{device_id}/selection/mode', {
          params: { path: { device_id: deviceId } },
          body: change,
        }),
      ),
    onSuccess: after,
  })
}

export function useClearSelection(deviceId: string) {
  const { api } = useEngine()
  const after = useAfterSelection(deviceId)
  return useMutation({
    mutationFn: async () =>
      unwrap(
        await api.POST('/api/v1/profiles/{device_id}/selection/clear', {
          params: { path: { device_id: deviceId } },
        }),
      ),
    onSuccess: after,
  })
}
