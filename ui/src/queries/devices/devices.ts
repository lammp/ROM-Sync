/**
 * Devices (F10-S10, S11, S22): what is attached, the profiles, and for one
 * profile its selection, its inventory, its plan and its capacity; the
 * selection changes, each answered by the engine's own rule; and making a
 * profile for a device, or adopting one another computer made (F10-S23).
 */
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import type { components } from '../../lib/api/api'
import { unwrap, useEngine, type Engine } from '../engine/engine'
import { useSettings, type Setting } from '../settings/settings'

export type Profile = components['schemas']['Profile']
export type Attached = components['schemas']['AttachedDevice']
export type Blocked = components['schemas']['BlockedDevice']
export type SelectionView = components['schemas']['SelectionView']
export type PlanView = components['schemas']['PlanView']

/** How often attached devices are asked for, in milliseconds, until the settings are read: the registry's default. */
export const PROBE_MS = 15_000

/** The probe interval the settings say (`device.probe_interval`, in seconds), in milliseconds. */
export function probeMs(settings: readonly Setting[] | undefined): number {
  const seconds = settings?.find((s) => s.key === 'device.probe_interval')?.value
  return typeof seconds === 'number' && seconds > 0 ? seconds * 1000 : PROBE_MS
}

/** The faster transport first, when one device is attached over more than one. */
const PREFERRED: readonly string[] = ['adb', 'volume', 'mtp']

/**
 * The device attached for a profile: the one the engine recognised as it,
 * over whichever transport it came back on. A profile's stored reference
 * names the transport it was made over, so a device plugged back in over
 * another (the Thor over MTP when ADB is not answering) is still this
 * profile. The one rule for "online" on every page (F11-S53).
 */
export function attachedFor(
  devices: readonly Attached[],
  profileId: string | null,
): Attached | null {
  if (!profileId) return null
  const mine = devices.filter((d) => d.profile?.id === profileId)
  const rank = (d: Attached) => {
    const i = PREFERRED.indexOf(d.kind)
    return i < 0 ? PREFERRED.length : i
  }
  return [...mine].sort((a, b) => rank(a) - rank(b))[0] ?? null
}

export function useAttached() {
  const { api } = useEngine()
  const settings = useSettings().data
  return useQuery({
    queryKey: ['devices'],
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/v1/devices', { signal })),
    refetchInterval: probeMs(settings),
  })
}

export function useProfiles() {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['profiles'],
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/v1/profiles', { signal })).profiles,
  })
}

type Api = Engine['api']

const selectionQuery = (api: Api, deviceId: string) => ({
  queryKey: ['selection', deviceId],
  queryFn: async ({ signal }: { signal: AbortSignal }) =>
    unwrap(
      await api.GET('/api/v1/profiles/{device_id}/selection', {
        params: { path: { device_id: deviceId } },
        signal,
      }),
    ),
})

const inventoryQuery = (api: Api, deviceId: string) => ({
  queryKey: ['inventory', deviceId],
  queryFn: async ({ signal }: { signal: AbortSignal }) =>
    unwrap(
      await api.GET('/api/v1/profiles/{device_id}/inventory', {
        params: { path: { device_id: deviceId } },
        signal,
      }),
    ).items,
})

const capacityQuery = (api: Api, ref: string) => ({
  queryKey: ['capacity', ref],
  queryFn: async ({ signal }: { signal: AbortSignal }) =>
    unwrap(await api.GET('/api/v1/devices/{ref}/capacity', { params: { path: { ref } }, signal })),
})

export function useSelection(deviceId: string | null) {
  const { api } = useEngine()
  return useQuery({ ...selectionQuery(api, deviceId ?? ''), enabled: deviceId !== null })
}

export function useInventory(deviceId: string | null) {
  const { api } = useEngine()
  return useQuery({ ...inventoryQuery(api, deviceId ?? ''), enabled: deviceId !== null })
}

/** Every profile's selection, in the order given, sharing `useSelection`'s cache. */
export function useSelections(deviceIds: readonly string[]) {
  const { api } = useEngine()
  return useQueries({ queries: deviceIds.map((id) => selectionQuery(api, id)) })
}

/** Every profile's contents as last read, in the order given. */
export function useInventories(deviceIds: readonly string[]) {
  const { api } = useEngine()
  return useQueries({ queries: deviceIds.map((id) => inventoryQuery(api, id)) })
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
  return useQuery({ ...capacityQuery(api, ref ?? ''), enabled: ref !== null })
}

/** Each attached device's space, asked of that device alone. */
export function useCapacities(refs: readonly string[]) {
  const { api } = useEngine()
  return useQueries({ queries: refs.map((ref) => capacityQuery(api, ref)) })
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

/** After a profile is made or adopted, what is attached and the profiles are read again. */
function useAfterProfile() {
  const client = useQueryClient()
  return () => {
    void client.invalidateQueries({ queryKey: ['devices'] })
    void client.invalidateQueries({ queryKey: ['profiles'] })
  }
}

export function useCreateProfile() {
  const { api } = useEngine()
  const after = useAfterProfile()
  return useMutation({
    mutationFn: async (p: { ref: string; name: string; writeMarker: boolean }) =>
      unwrap(
        await api.POST('/api/v1/devices/{ref}/profile', {
          params: { path: { ref: p.ref } },
          body: { name: p.name, write_marker: p.writeMarker },
        }),
      ),
    onSuccess: after,
  })
}

/** Rebuilds a profile from another computer's marker; the engine trusts it whole or not at all. */
export function useAdopt() {
  const { api } = useEngine()
  const after = useAfterProfile()
  return useMutation({
    mutationFn: async (ref: string) =>
      unwrap(await api.POST('/api/v1/devices/{ref}/adopt', { params: { path: { ref } } })),
    onSuccess: after,
  })
}

/** A device's sync runs, newest first. */
export function useRuns(deviceId: string | null) {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['runs', deviceId ?? ''],
    enabled: deviceId !== null,
    queryFn: async ({ signal }) =>
      unwrap(
        await api.GET('/api/v1/profiles/{device_id}/runs', {
          params: { path: { device_id: deviceId ?? '' } },
          signal,
        }),
      ).runs,
  })
}

/** A profile's new name; the device keeps the old one until its marker is written. */
export function useRename(deviceId: string) {
  const { api } = useEngine()
  const after = useAfterProfile()
  return useMutation({
    mutationFn: async (name: string) =>
      unwrap(
        await api.POST('/api/v1/profiles/{device_id}/rename', {
          params: { path: { device_id: deviceId } },
          body: { name },
        }),
      ),
    onSuccess: after,
  })
}

/** Reads the device's games into its inventory, read-only, as a job on the device. */
export function useScan(ref: string) {
  const { api } = useEngine()
  return useMutation({
    mutationFn: async () =>
      unwrap(await api.POST('/api/v1/devices/{ref}/scan', { params: { path: { ref } } })),
  })
}

/** Writes the profile's marker to the device again, as a job on the device. */
export function useWriteMarker(ref: string) {
  const { api } = useEngine()
  return useMutation({
    mutationFn: async () =>
      unwrap(await api.POST('/api/v1/devices/{ref}/marker', { params: { path: { ref } } })),
  })
}
