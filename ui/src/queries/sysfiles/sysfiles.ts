/**
 * System files (F10-S19): the store's copies with no device, a device's
 * readiness from its last survey, and the survey, stage, unstage and
 * remove-stray jobs on the device's reference.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import type { components } from '../../lib/api/api'
import { unwrap, useEngine } from '../engine/engine'

export type SysReport = components['schemas']['SysReport']
export type SysSystem = components['schemas']['SysSystem']
export type SysStoreItem = components['schemas']['SysStoreItem']

/**
 * Every requirement with the store's copy only. The engine reads the bios
 * folder afresh each time it is asked, so the page asks again whenever the
 * window comes back into focus: a file added or removed in Explorer shows
 * on return, and the reload icon asks at once.
 */
export function useStoreSysfiles() {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['sysfiles', 'store'],
    refetchOnWindowFocus: true,
    queryFn: async ({ signal }) =>
      unwrap(await api.GET('/api/v1/sysfiles/store', { signal })).items,
  })
}

/** A device's readiness from its last survey; reads nothing from the device. */
export function useSysReport(ref: string | null) {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['sysfiles', ref ?? ''],
    enabled: ref !== null,
    // the store's side is read afresh; the device's is the last survey
    refetchOnWindowFocus: true,
    queryFn: async ({ signal }) =>
      unwrap(
        await api.GET('/api/v1/devices/{ref}/sysfiles', {
          params: { path: { ref: ref ?? '' } },
          signal,
        }),
      ),
  })
}

/** The report read again once a job on the device's files ends. */
export function useAfterSysfiles(ref: string | null) {
  const client = useQueryClient()
  return useCallback(() => {
    if (ref !== null) void client.invalidateQueries({ queryKey: ['sysfiles', ref] })
  }, [client, ref])
}

/** Lists the device's staging and emulator folders, read-only, as a job. */
export function useSurvey(ref: string) {
  const { api } = useEngine()
  return useMutation({
    mutationFn: async () =>
      unwrap(
        await api.POST('/api/v1/devices/{ref}/sysfiles/survey', { params: { path: { ref } } }),
      ),
  })
}

/** Copies a system's files from the store to its staging folder, as a job. */
export function useStage(ref: string) {
  const { api } = useEngine()
  return useMutation({
    mutationFn: async (system: string) =>
      unwrap(
        await api.POST('/api/v1/devices/{ref}/sysfiles/{system}/stage', {
          params: { path: { ref, system } },
        }),
      ),
  })
}

/** Deletes a system's staged files from the device, as a job. */
export function useUnstage(ref: string) {
  const { api } = useEngine()
  return useMutation({
    mutationFn: async (system: string) =>
      unwrap(
        await api.POST('/api/v1/devices/{ref}/sysfiles/{system}/unstage', {
          params: { path: { ref, system } },
        }),
      ),
  })
}

/** Deletes one stray item under the staging root, as a job. */
export function useRemoveOther(ref: string) {
  const { api } = useEngine()
  return useMutation({
    mutationFn: async (item: { path: string; name: string }) =>
      unwrap(
        await api.POST('/api/v1/devices/{ref}/sysfiles/remove-other', {
          params: { path: { ref } },
          body: item,
        }),
      ),
  })
}
