/**
 * The library, read (F10-S7): every game prepared once for search, facets
 * and sort, each cover as the address the engine serves it at (F10-S21).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import type { components } from '../../lib/api/api'
import { prepare, type Game } from '../../lib/game/game'
import { unwrap, useEngine } from '../engine/engine'

export type Summary = components['schemas']['GameSummary']
/** A game as listed: prepared, with its cover's address and its match state (pending, matched, not found). */
export type ListedGame = Game & { readonly coverUrl: string | null; readonly state: string }
export type Catalogue = {
  readonly games: readonly ListedGame[]
  readonly systems: Readonly<Record<string, string>>
}

export const LIBRARY_KEY = ['library'] as const

export function coverUrl(cover: string | null): string | null {
  return cover ? `/api/v1/covers/${encodeURIComponent(cover)}` : null
}

/** The engine's games and systems as the interface lists them. */
export function catalogue(
  games: readonly Summary[],
  systems: readonly { key: string; label: string }[],
): Catalogue {
  const labels = Object.fromEntries(systems.map((s) => [s.key, s.label]))
  return {
    games: games.map((g) => ({
      ...prepare(g, labels),
      coverUrl: coverUrl(g.cover),
      state: g.state,
    })),
    systems: labels,
  }
}

export function useLibrary() {
  const { api } = useEngine()
  return useQuery({
    queryKey: LIBRARY_KEY,
    queryFn: async ({ signal }) => {
      const [library, systems] = await Promise.all([
        api.GET('/api/v1/library', { signal }).then(unwrap),
        api.GET('/api/v1/systems', { signal }).then(unwrap),
      ])
      return catalogue(library.games, systems.systems)
    },
  })
}

/** The store's systems with their game counts and sizes. */
export function useSystems() {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['systems'],
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/v1/systems', { signal })).systems,
  })
}

export function useGame(id: number | null) {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['game', id ?? 0],
    enabled: id !== null,
    queryFn: async ({ signal }) =>
      unwrap(
        await api.GET('/api/v1/games/{game_id}', {
          params: { path: { game_id: id ?? 0 } },
          signal,
        }),
      ),
  })
}

/** Pins a game to a metadata entry, as a job; the library is read again when it ends. */
export function useRematch(id: number) {
  const { api } = useEngine()
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (ref: string) =>
      unwrap(
        await api.POST('/api/v1/games/{game_id}/rematch', {
          params: { path: { game_id: id } },
          body: { ref },
        }),
      ),
    onSettled: () => client.invalidateQueries({ queryKey: ['game', id] }),
  })
}

/** The library's own jobs, each started with nothing but its name. */
type LibraryJob = '/api/v1/library/scan' | '/api/v1/library/franchises'

/** Starts one of the library's jobs: scan the store, or propose franchise tags. */
export function useLibraryJob(path: LibraryJob) {
  const { api } = useEngine()
  return useMutation({
    mutationFn: async () => unwrap(await api.POST(path, {})),
  })
}

/**
 * The one metadata action (F5-S12): match the games that need it, or every
 * game but a pin on a refresh, then fill missing covers from libretro.
 */
export function useMetadataJob() {
  const { api } = useEngine()
  return useMutation({
    mutationFn: async (refresh: boolean) =>
      unwrap(await api.POST('/api/v1/library/metadata', { body: { refresh } })),
  })
}

/** After a library job ends: the library, its systems and the job list are read again. */
export function useAfterLibraryJob() {
  const client = useQueryClient()
  return useCallback(() => {
    for (const queryKey of [LIBRARY_KEY, ['systems'], ['jobs']])
      void client.invalidateQueries({ queryKey })
  }, [client])
}
