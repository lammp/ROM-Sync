import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { fakeFetch, freshWorld } from '../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../engine/engine'
import { appStore } from '../../store/store'
import { useAnnounce, usePickFolder, useReveal, useShell, useVersion } from './meta'

const calls: { path: string; body: string }[] = []

function harness() {
  const fetch = fakeFetch(freshWorld())
  const engine = createEngine({
    fetch: (async (r: Request) => {
      const url = new URL(r.url).pathname
      if (url.startsWith('/api/v1/shell/')) {
        calls.push({ path: url, body: await r.clone().text() })
        return Response.json(url.endsWith('pick-folder') ? { path: 'E:\\ROMs' } : { done: true })
      }
      return fetch(r)
    }) as typeof globalThis.fetch,
    baseUrl: 'http://engine.test',
    retry: 0,
  })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <EngineProvider engine={engine}>{children}</EngineProvider>
  )
  return { wrapper }
}

describe('engine facts and shell actions', () => {
  it('reads the version, who hosts the page and what the shell answers', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(() => ({ version: useVersion(), shell: useShell() }), { wrapper })
    await waitFor(() =>
      expect(result.current.shell.data).toEqual({
        kind: 'browser',
        capabilities: ['reveal', 'pick_folder', 'browse_folders', 'open_url', 'notify'],
      }),
    )
    expect(result.current.version.data?.version).toBe('2.0.0')
  })

  it('asks the shell for a folder and to reveal one the engine knows by name', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(() => ({ pick: usePickFolder(), reveal: useReveal() }), {
      wrapper,
    })
    await act(async () => {
      expect(await result.current.pick.mutateAsync('Choose the store folder')).toBe('E:\\ROMs')
      await result.current.reveal.mutateAsync({ root: 'data' })
    })
    expect(calls.map((c) => [c.path, JSON.parse(c.body)])).toEqual([
      ['/api/v1/shell/pick-folder', { title: 'Choose the store folder' }],
      ['/api/v1/shell/reveal', { root: 'data', path: null }],
    ])
  })
})

/** A notify endpoint that delivers, refuses, fails, or cannot be reached at all. */
function announcing(
  answer: 'delivered' | 'not delivered' | 'error' | 'unreachable',
  capabilities: ('reveal' | 'pick_folder' | 'open_url' | 'notify')[] = ['notify'],
) {
  const world = freshWorld()
  world.shell = { kind: 'desktop', capabilities }
  const fetch = fakeFetch(world)
  const sent: string[] = []
  const engine = createEngine({
    fetch: (async (r: Request) => {
      if (new URL(r.url).pathname === '/api/v1/shell/notify') {
        sent.push((JSON.parse(await r.clone().text()) as { body: string }).body)
        if (answer === 'unreachable') throw new TypeError('Failed to fetch')
        if (answer === 'error')
          return Response.json(
            { error: { code: 'shell.unavailable', message: 'no' } },
            { status: 403 },
          )
        return Response.json({ delivered: answer === 'delivered' })
      }
      return fetch(r)
    }) as typeof globalThis.fetch,
    baseUrl: 'http://engine.test',
    retry: 0,
  })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <EngineProvider engine={engine}>{children}</EngineProvider>
  )
  return { wrapper, sent }
}

const LONG = { started: '2026-10-12T10:00:00Z', finished: '2026-10-12T10:00:45Z' }
const SHORT = { started: '2026-10-12T10:00:00Z', finished: '2026-10-12T10:00:05Z' }
const toasts = () => appStore.getState().ui.toasts.map((t) => [t.text, t.tone])

async function ready(wrapper: ({ children }: { children: ReactNode }) => ReactNode) {
  const hook = renderHook(() => ({ shell: useShell(), announce: useAnnounce() }), { wrapper })
  await waitFor(() => expect(hook.result.current.shell.data?.kind).toBe('desktop'))
  return hook.result
}

describe('announcing a finished job', () => {
  it('notifies for a job over thirty seconds, and toasts it as well', async () => {
    const { wrapper, sent } = announcing('delivered')
    const result = await ready(wrapper)
    act(() => result.current.announce(LONG, 'Scan done: 40 games'))
    await waitFor(() => expect(sent).toEqual(['Scan done: 40 games']))
    expect(toasts()).toEqual([['Scan done: 40 games', 'info']])
  })

  it('leaves a short job, or a shell that cannot notify, to the toast alone', async () => {
    const short = announcing('delivered')
    const a = await ready(short.wrapper)
    act(() => a.current.announce(SHORT, 'Marker written'))
    act(() => a.current.announce(undefined, 'Nothing known'))
    const unable = announcing('delivered', ['reveal'])
    const b = await ready(unable.wrapper)
    act(() => b.current.announce(LONG, 'Synced', true))
    expect(short.sent).toEqual([])
    expect(unable.sent).toEqual([])
    expect(toasts()).toEqual([
      ['Marker written', 'info'],
      ['Nothing known', 'info'],
      ['Synced', 'bad'],
    ])
  })

  it.each(['not delivered', 'error', 'unreachable'] as const)(
    'test_notify_falls_back: a notification that is %s does not lose the message',
    async (answer) => {
      const { wrapper, sent } = announcing(answer)
      const result = await ready(wrapper)
      act(() => result.current.announce(LONG, 'Sync failed: device gone', true))
      await waitFor(() => expect(sent).toHaveLength(1))
      await new Promise((r) => setTimeout(r, 0))
      expect(toasts()).toEqual([['Sync failed: device gone', 'bad']])
    },
  )
})
