/** What the engine says about itself: its version, and who hosts the page. */
import { useMutation, useQuery } from '@tanstack/react-query'
import { shellOf } from '../../lib/platform/platform'
import { unwrap, useEngine } from '../engine/engine'

export function useVersion() {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['version'],
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/v1/version', { signal })),
  })
}

/** Who hosts the page and which shell actions (browse, reveal, open) answer here (F12-S3). */
export function useShell() {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['session'],
    queryFn: async ({ signal }) => shellOf(unwrap(await api.GET('/api/v1/session', { signal }))),
  })
}

/** Asks the desktop shell for a folder; null when the person cancels. */
export function usePickFolder() {
  const { api } = useEngine()
  return useMutation({
    mutationFn: async (title: string) =>
      unwrap(await api.POST('/api/v1/shell/pick-folder', { body: { title } })).path,
  })
}

/** Shows a folder the engine knows by name (store, data, logs) in the file manager. */
export function useReveal() {
  const { api } = useEngine()
  return useMutation({
    mutationFn: async (where: { root: string; path?: string | null }) =>
      unwrap(
        await api.POST('/api/v1/shell/reveal', {
          body: { root: where.root, path: where.path ?? null },
        }),
      ),
  })
}
