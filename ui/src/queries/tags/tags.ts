/** A game's tags (F10-S18): read, added, decided and removed; a decision stands against later passes. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { components } from '../../lib/api/api'
import { unwrap, useEngine } from '../engine/engine'
import { LIBRARY_KEY } from '../library/library'

export type TagList = components['schemas']['TagList']

export function useTags(gameId: number | null) {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['tags', gameId ?? 0],
    enabled: gameId !== null,
    queryFn: async ({ signal }) =>
      unwrap(
        await api.GET('/api/v1/games/{game_id}/tags', {
          params: { path: { game_id: gameId ?? 0 } },
          signal,
        }),
      ),
  })
}

type Change =
  | { readonly op: 'add'; readonly tag: string; readonly kind: string }
  | { readonly op: 'decide'; readonly tag: string; readonly kind: string; readonly accept: boolean }
  | { readonly op: 'remove'; readonly tag: string; readonly kind: string }

/** Every tag change answers with the game's tags; the library is read again for facets and search. */
export function useTagChange(gameId: number) {
  const { api } = useEngine()
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (c: Change) => {
      const path = { params: { path: { game_id: gameId } } }
      if (c.op === 'add')
        return unwrap(
          await api.POST('/api/v1/games/{game_id}/tags', {
            ...path,
            body: { tag: c.tag, kind: c.kind },
          }),
        )
      if (c.op === 'decide')
        return unwrap(
          await api.POST('/api/v1/games/{game_id}/tags/decide', {
            ...path,
            body: { tag: c.tag, kind: c.kind, accept: c.accept },
          }),
        )
      return unwrap(
        await api.POST('/api/v1/games/{game_id}/tags/remove', {
          ...path,
          body: { tag: c.tag, kind: c.kind },
        }),
      )
    },
    onSuccess: (tags) => {
      client.setQueryData(['tags', gameId], tags)
      void client.invalidateQueries({ queryKey: LIBRARY_KEY })
    },
  })
}
