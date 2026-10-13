/** What the engine says about itself: its version, and who hosts the page. */
import { useMutation, useQuery } from '@tanstack/react-query'
import { useCallback } from 'react'
import { BROWSER, can, ranLong, shellOf } from '../../lib/platform/platform'
import { appStore } from '../../store/store'
import { unwrap, useEngine } from '../engine/engine'

export function useVersion() {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['version'],
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/v1/version', { signal })),
  })
}

/** What the Diagnostics section shows, read from the engine each time (F15-S1). */
export function useDiagnostics() {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['diagnostics'],
    queryFn: async ({ signal }) => unwrap(await api.GET('/api/v1/diagnostics', { signal })),
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

/**
 * One folder of this computer while choosing by browsing (F11-S45): the
 * drives when `path` is null. Files are listed only of the `files` kinds.
 * Asked only while the browser is open.
 */
export function useFolders(path: string | null, files: readonly string[], enabled: boolean) {
  const { api } = useEngine()
  return useQuery({
    queryKey: ['folders', path ?? '', files.join(',')],
    enabled,
    retry: false,
    queryFn: async ({ signal }) =>
      unwrap(
        await api.GET('/api/v1/shell/folders', {
          params: { query: { path: path ?? undefined, files: [...files] } },
          signal,
        }),
      ),
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

type Ended = { readonly started: string | null; readonly finished: string | null }

/**
 * Says how a job ended (F12-S5). The toast is always shown and is the record
 * of what happened; a job that ran over thirty seconds is also announced as a
 * system notification where the shell can show one. A notification that
 * fails, or is not delivered, changes nothing: the toast is already up.
 */
export function useAnnounce() {
  const { api } = useEngine()
  const shell = useShell().data ?? BROWSER
  return useCallback(
    (job: Ended | undefined, text: string, bad = false) => {
      appStore.getState().ui.toast(text, bad ? 'bad' : 'info')
      if (!job || !can(shell, 'notify') || !ranLong(job)) return
      api
        .POST('/api/v1/shell/notify', { body: { title: 'ROM-Sync', body: text } })
        .catch(() => undefined)
    },
    [api, shell],
  )
}
