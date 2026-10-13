/** What the engine says about itself: its version, and who hosts the page. */
import { useMutation, useQuery } from '@tanstack/react-query'
import { useCallback } from 'react'
import type { Notice } from '../../lib/notices/notices'
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

type Ended = {
  readonly id?: string
  readonly started: string | null
  readonly finished: string | null
}

/** What `useAnnounce` is given: a sentence, or the notification itself. */
type Said = string | Omit<Notice, 'at'>

/**
 * Says how a job ended (F12-S5, F11-S47). It is recorded once as a
 * notification, under the job's id, and said once as a toast: whichever of
 * the page that ran the job or the notification watcher says it first, the
 * other finds it said. A job that ran over thirty seconds is also announced
 * as a system notification where the shell can show one; one that fails, or
 * is not delivered, changes nothing.
 */
export function useAnnounce() {
  const { api } = useEngine()
  const shell = useShell().data ?? BROWSER
  return useCallback(
    (job: Ended | undefined, said: Said, bad = false) => {
      const notice: Omit<Notice, 'at'> | null =
        typeof said !== 'string'
          ? said
          : job?.id
            ? { id: `job:${job.id}`, source: 'job', tone: bad ? 'bad' : 'info', title: said }
            : null
      const ui = appStore.getState().ui
      if (notice && !ui.notify({ ...notice, at: Date.now() })) return
      const text = notice ? [notice.title, notice.body].filter(Boolean).join('. ') : String(said)
      ui.toast(text, notice ? (notice.tone === 'bad' ? 'bad' : 'info') : bad ? 'bad' : 'info')
      if (!job || !can(shell, 'notify') || !ranLong(job)) return
      api
        .POST('/api/v1/shell/notify', { body: { title: 'ROM-Sync', body: text } })
        .catch(() => undefined)
    },
    [api, shell],
  )
}
