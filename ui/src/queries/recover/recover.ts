/**
 * Recover (F10-S20): what a device holds that the library does not, from what
 * was last read of it, and pulling one item back into the store, never over
 * a file the store already has.
 */
import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import type { components } from '../../lib/api/api'
import { unwrap, useEngine } from '../engine/engine'

export type RecoverItem = components['schemas']['RecoverItem']

/** Each attached device's items that only it holds, in the order given. */
export function useRecoverLists(refs: readonly string[]) {
  const { api } = useEngine()
  return useQueries({
    queries: refs.map((ref) => ({
      queryKey: ['recover', ref],
      queryFn: async ({ signal }: { signal: AbortSignal }) =>
        unwrap(
          await api.GET('/api/v1/devices/{ref}/recover', { params: { path: { ref } }, signal }),
        ).items,
    })),
  })
}

/** Pulls one item off the device and places it in the store, as a job on the device. */
export function useRecover(ref: string) {
  const { api } = useEngine()
  return useMutation({
    mutationFn: async (item: { system: string; name: string }) =>
      unwrap(
        await api.POST('/api/v1/devices/{ref}/recover', { params: { path: { ref } }, body: item }),
      ),
  })
}

/** After a recover ends: every device's list, and the library, read again. */
export function useAfterRecover() {
  const client = useQueryClient()
  return useCallback(() => {
    for (const queryKey of [['recover'], ['library'], ['systems']])
      void client.invalidateQueries({ queryKey })
  }, [client])
}
