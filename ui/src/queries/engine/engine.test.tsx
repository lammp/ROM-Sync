import { renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import {
  EngineError,
  EngineProvider,
  TOKEN_HEADER,
  createEngine,
  unwrap,
  useEngine,
} from './engine'

type Seen = { method: string; url: string; token: string | null }

function fakeEngine(sessions: string[] = ['tok-1']) {
  const seen: Seen[] = []
  const fetch = async (request: Request) => {
    seen.push({
      method: request.method,
      url: new URL(request.url).pathname,
      token: request.headers.get(TOKEN_HEADER),
    })
    if (request.url.endsWith('/api/v1/session')) {
      const token = sessions.shift()
      return token
        ? Response.json({ token, kind: 'browser', capabilities: [] })
        : Response.json({ error: { code: 'request.refused', message: 'no' } }, { status: 403 })
    }
    return Response.json({ id: 'j1', kind: 'scan', state: 'cancelling' })
  }
  return {
    engine: createEngine({
      baseUrl: 'http://127.0.0.1:8765',
      fetch: fetch as typeof globalThis.fetch,
    }),
    seen,
  }
}

describe('engine', () => {
  it('sends the session token on a change and never on a read', async () => {
    const { engine, seen } = fakeEngine()
    await engine.api.GET('/api/v1/jobs/{job_id}', { params: { path: { job_id: 'j1' } } })
    await engine.api.POST('/api/v1/jobs/{job_id}/cancel', { params: { path: { job_id: 'j1' } } })
    await engine.api.POST('/api/v1/jobs/{job_id}/cancel', { params: { path: { job_id: 'j1' } } })
    expect(seen).toEqual([
      { method: 'GET', url: '/api/v1/jobs/j1', token: null },
      { method: 'GET', url: '/api/v1/session', token: null },
      { method: 'POST', url: '/api/v1/jobs/j1/cancel', token: 'tok-1' },
      { method: 'POST', url: '/api/v1/jobs/j1/cancel', token: 'tok-1' },
    ])
  })

  it('asks for the session again after a refusal', async () => {
    const { engine, seen } = fakeEngine([])
    const cancel = () =>
      engine.api.POST('/api/v1/jobs/{job_id}/cancel', { params: { path: { job_id: 'j1' } } })
    await expect(cancel()).rejects.toThrow(EngineError)
    await expect(cancel()).rejects.toThrow('no')
    expect(seen.filter((s) => s.url === '/api/v1/session')).toHaveLength(2)
  })

  it('unwraps data, and throws the envelope or the status', () => {
    const ok = new Response(null, { status: 200 })
    expect(unwrap({ data: 1, response: ok })).toBe(1)
    const bad = new Response(null, { status: 404, statusText: 'Not Found' })
    expect(() =>
      unwrap({
        error: { error: { code: 'job.not_found', message: 'gone', field: 'job_id' } },
        response: bad,
      }),
    ).toThrow(expect.objectContaining({ code: 'job.not_found', message: 'gone', field: 'job_id' }))
    expect(() => unwrap({ error: 'text', response: bad })).toThrow(
      expect.objectContaining({ code: 'http.404', message: 'Not Found', field: null }),
    )
  })

  it('is provided to the features beneath it, and refused outside', () => {
    const { engine } = fakeEngine()
    const wrapper = ({ children }: { children: ReactNode }) => (
      <EngineProvider engine={engine}>{children}</EngineProvider>
    )
    expect(renderHook(() => useEngine(), { wrapper }).result.current).toBe(engine)
    expect(() => renderHook(() => useEngine())).toThrow('outside an EngineProvider')
    const own = renderHook(() => useEngine(), { wrapper: EngineProvider }).result.current
    expect(own.pollMs).toBe(1000)
  })
})
