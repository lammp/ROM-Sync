import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { GUARDED, NetworkInTest } from '../../../structure/guard/network'
import { EngineProvider, createEngine } from '../engine/engine'
import { fakeFetch, freshWorld } from '../../../e2e/fake/world'
import { finished, useCancelJob, useJob, useJobs, type Job } from './job'

const job = (state: string): Job => ({
  id: 'j1',
  kind: 'sync',
  state,
  target: null,
  started: null,
  finished: null,
  progress: null,
  result: null,
  error_code: null,
  error_message: null,
})

/** A fake engine whose job answers come from a script; the last answer repeats. */
function scripted(states: (string | 'hang')[]) {
  const calls: { url: string; signal: AbortSignal }[] = []
  const fetch = (request: Request) => {
    calls.push({ url: new URL(request.url).pathname, signal: request.signal })
    if (request.url.endsWith('/session'))
      return Promise.resolve(Response.json({ token: 't', kind: 'browser', capabilities: [] }))
    const state = states.length > 1 ? states.shift() : states[0]
    if (state === 'hang')
      return new Promise<Response>((_, reject) =>
        request.signal.addEventListener('abort', () => reject(request.signal.reason)),
      )
    return Promise.resolve(Response.json(job(state ?? 'running')))
  }
  const engine = createEngine({
    fetch: fetch as typeof globalThis.fetch,
    pollMs: 1000,
    retry: 0,
    baseUrl: 'http://e',
  })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <EngineProvider engine={engine}>{children}</EngineProvider>
  )
  return { calls, wrapper, engine }
}

afterEach(() => {
  vi.useRealTimers()
})

describe('job', () => {
  it('polls a running job and stops when it finishes', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const { calls, wrapper } = scripted(['running', 'running', 'done'])
    const { result } = renderHook(() => useJob('j1'), { wrapper })
    await waitFor(() => expect(result.current.data?.state).toBe('running'))
    await act(() => vi.advanceTimersByTimeAsync(1000))
    await act(() => vi.advanceTimersByTimeAsync(1000))
    await waitFor(() => expect(result.current.data?.state).toBe('done'))
    const polls = calls.length
    await act(() => vi.advanceTimersByTimeAsync(5000))
    expect(calls).toHaveLength(polls)
    expect(polls).toBe(3)
  })

  it('cancels_on_navigation', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const { calls, wrapper } = scripted(['running', 'hang'])
    const { result, unmount } = renderHook(() => useJob('j1'), { wrapper })
    await waitFor(() => expect(result.current.data?.state).toBe('running'))
    await act(() => vi.advanceTimersByTimeAsync(1000))
    await waitFor(() => expect(calls).toHaveLength(2))
    const inFlight = calls[1]?.signal
    expect(inFlight?.aborted).toBe(false)
    unmount()
    await waitFor(() => expect(inFlight?.aborted).toBe(true))
    await act(() => vi.advanceTimersByTimeAsync(10_000))
    expect(calls).toHaveLength(2)
  })

  it('asks for nothing without a job', async () => {
    const { calls, wrapper } = scripted(['running'])
    const { result } = renderHook(() => useJob(null), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
    expect(calls).toHaveLength(0)
  })

  it('cancels a job and shows the answer at once', async () => {
    const { wrapper, engine } = scripted(['cancelling'])
    const { result } = renderHook(() => useCancelJob(), { wrapper })
    await act(() => result.current.mutateAsync('j1'))
    expect(engine.client.getQueryData(['job', 'j1'])).toMatchObject({ state: 'cancelling' })
  })

  it('knows which states are final', () => {
    expect([undefined, job('running'), job('cancelling')].map(finished)).toEqual([
      false,
      false,
      false,
    ])
    expect(['done', 'failed', 'cancelled'].map((s) => finished(job(s)))).toEqual([true, true, true])
  })

  it('no_network_in_tests', async () => {
    expect((globalThis.fetch as unknown as Record<symbol, boolean>)[GUARDED]).toBe(true)
    await expect(fetch('http://127.0.0.1:8765/api/v1/version')).rejects.toThrow(NetworkInTest)
    await expect(fetch(new Request('http://example.test/'))).rejects.toThrow(
      'fetch http://example.test/',
    )
    expect(() => new WebSocket('ws://127.0.0.1:8765')).toThrow(NetworkInTest)
    expect(() => new EventSource('http://127.0.0.1:8765/events')).toThrow(NetworkInTest)
    expect(() => new XMLHttpRequest().open('GET', 'http://127.0.0.1:8765/')).toThrow(NetworkInTest)
    const { calls, wrapper } = scripted(['running'])
    const { result } = renderHook(() => useJob('j1'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(calls.map((c) => c.url)).toEqual(['/api/v1/jobs/j1'])
  })

  it('lists every job, newest first, and asks again only while one runs', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const world = freshWorld()
    world.jobs.push({ ...job('done'), id: 'a' }, { ...job('running'), id: 'b' })
    const fetch = fakeFetch(world)
    let asked = 0
    const engine = createEngine({
      fetch: ((r: Request) => {
        if (new URL(r.url).pathname === '/api/v1/jobs') asked++
        return fetch(r)
      }) as typeof globalThis.fetch,
      baseUrl: 'http://e',
      retry: 0,
      pollMs: 1000,
    })
    const wrapper = ({ children }: { children: ReactNode }) => (
      <EngineProvider engine={engine}>{children}</EngineProvider>
    )
    const { result } = renderHook(() => useJobs(), { wrapper })
    await waitFor(() => expect(result.current.data?.map((j) => j.id)).toEqual(['b', 'a']))
    const running = world.jobs.find((j) => j.id === 'b')
    if (running) running.state = 'done'
    await act(() => vi.advanceTimersByTimeAsync(1000))
    await waitFor(() => expect(result.current.data?.[0]?.state).toBe('done'))
    const seen = asked
    await act(() => vi.advanceTimersByTimeAsync(5000))
    expect(asked).toBe(seen)
  })
})
