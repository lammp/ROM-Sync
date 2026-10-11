import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { THOR_REF, fakeFetch, freshWorld, type World } from '../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../engine/engine'
import {
  sampleOf,
  useAfterDeviceJob,
  useCancelSync,
  useStartSync,
  useSyncStatus,
  type SyncStatus,
} from './sync'

function harness(world: World = freshWorld()) {
  const calls: string[] = []
  const fetch = fakeFetch(world)
  const engine = createEngine({
    fetch: ((r: Request) => {
      calls.push(`${r.method} ${new URL(r.url).pathname}`)
      return fetch(r)
    }) as typeof globalThis.fetch,
    baseUrl: 'http://engine.test',
    retry: 0,
    pollMs: 1000,
  })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <EngineProvider engine={engine}>{children}</EngineProvider>
  )
  return { world, engine, wrapper, calls }
}

const job = (
  state: string,
  detail: Record<string, number> | null,
  result: Record<string, number> | null = null,
) =>
  ({
    id: 'j',
    kind: 'sync',
    target: THOR_REF,
    state,
    progress: detail ? { phase: 'send', done: 1, total: 4, current: 'A.sfc', detail } : null,
    result,
    error_code: null,
    error_message: null,
    started: null,
    finished: null,
  }) as SyncStatus['job']

describe('sync queries', () => {
  it('reads a running sync’s totals from its job progress', () => {
    const status: SyncStatus = {
      job: job('running', { bytes_done: 300, bytes_removed: 20, sent: 1, removed: 2 }),
      run: {
        id: 7,
        started: 'x',
        finished: null,
        state: 'running',
        counts: null,
        bytes_moved: null,
      },
    }
    expect(sampleOf(status)).toEqual({
      run: '7',
      bytes_done: 300,
      bytes_removed: 20,
      status: {
        state: 'running',
        phase: 'send',
        current: 'A.sfc',
        sent: 1,
        removed: 2,
        failed: undefined,
      },
    })
  })

  it('reads a finished sync from its run record', () => {
    const status: SyncStatus = {
      job: job('done', null, { run: 7, send: 3 }),
      run: {
        id: 7,
        started: 'x',
        finished: 'y',
        state: 'failed',
        counts: { send: 3, remove: 1, failed: 2, error: 'dest.unavailable' },
        bytes_moved: 900,
      },
    }
    expect(sampleOf(status)).toMatchObject({
      run: '7',
      bytes_done: 900,
      status: { state: 'failed', sent: 3, removed: 1, failed: 2 },
    })
    expect(sampleOf({ job: null, run: null })).toMatchObject({ run: null, bytes_done: 0 })
  })

  it('asks for the status at the poll interval only while watching', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const { wrapper, calls } = harness()
      const { rerender } = renderHook(({ on }) => useSyncStatus(THOR_REF, on), {
        wrapper,
        initialProps: { on: true },
      })
      await waitFor(() => expect(calls.filter((c) => c.endsWith('/sync'))).toHaveLength(1))
      await act(() => vi.advanceTimersByTimeAsync(1000))
      await waitFor(() => expect(calls.filter((c) => c.endsWith('/sync'))).toHaveLength(2))
      rerender({ on: false })
      await act(() => vi.advanceTimersByTimeAsync(5000))
      expect(calls.filter((c) => c.endsWith('/sync'))).toHaveLength(2)
    } finally {
      vi.useRealTimers()
    }
  })

  it('starts a sync, refuses a second, and cancels the one running', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(
      () => ({ start: useStartSync(THOR_REF), cancel: useCancelSync(THOR_REF) }),
      { wrapper },
    )
    let id = ''
    await act(async () => {
      id = (await result.current.start.mutateAsync(null)).id
    })
    await expect(result.current.start.mutateAsync(null)).rejects.toMatchObject({
      code: 'job.conflict',
    })
    let state = ''
    await act(async () => {
      state = (await result.current.cancel.mutateAsync()).state
    })
    expect([id.startsWith('job-'), state]).toEqual([true, 'cancelled'])
  })

  it('asks for the removal count to be confirmed when there are many, and starts when it is', async () => {
    const world = freshWorld()
    world.inventory['dev-1'] = world.games.map((g) => ({
      system: g.system,
      name: g.name,
      kind: g.kind,
      size: g.size,
    }))
    world.selections['dev-1'] = {
      modes: { snes: 'none', gba: 'none', n64: 'none', ps2: 'none' },
      overrides: {},
    }
    const { wrapper } = harness(world)
    const { result } = renderHook(() => useStartSync(THOR_REF), { wrapper })
    await expect(result.current.mutateAsync(null)).rejects.toMatchObject({
      code: 'sync.confirm_removals',
    })
    await act(async () => {
      await result.current.mutateAsync(40)
    })
    expect(world.syncs[THOR_REF]?.job.state).toBe('running')
  })

  it('reads again what a device job may have changed', () => {
    const { wrapper, engine } = harness()
    const keys = [
      ['inventory', 'dev-1'],
      ['runs', 'dev-1'],
      ['selection', 'dev-1'],
      ['profiles'],
      ['plan', THOR_REF],
      ['capacity', THOR_REF],
      ['sync', THOR_REF],
    ]
    for (const k of keys) engine.client.setQueryData(k, { stale: true })
    const { result } = renderHook(() => useAfterDeviceJob('dev-1', THOR_REF), { wrapper })
    result.current()
    expect(keys.map((k) => engine.client.getQueryState(k)?.isInvalidated)).toEqual(
      keys.map(() => true),
    )
    const unplugged = renderHook(() => useAfterDeviceJob('dev-2', null), { wrapper })
    engine.client.setQueryData(['plan', THOR_REF], { stale: true })
    unplugged.result.current()
    expect(engine.client.getQueryState(['plan', THOR_REF])?.isInvalidated).toBe(false)
  })
})
