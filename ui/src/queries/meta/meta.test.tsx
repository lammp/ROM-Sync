import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { fakeFetch, freshWorld } from '../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../engine/engine'
import { usePickFolder, useReveal, useShell, useVersion } from './meta'

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
        capabilities: ['reveal', 'pick_folder', 'open_url'],
      }),
    )
    expect(result.current.version.data?.version).toBe('2.0.0.dev0')
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
