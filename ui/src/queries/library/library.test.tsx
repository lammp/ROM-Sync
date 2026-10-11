import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { fakeFetch, freshWorld } from '../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../engine/engine'
import { catalogue, coverUrl, useGame, useLibrary, useRematch } from './library'

function harness() {
  const world = freshWorld()
  const engine = createEngine({ fetch: fakeFetch(world), baseUrl: 'http://engine.test', retry: 0 })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <EngineProvider engine={engine}>{children}</EngineProvider>
  )
  return { world, engine, wrapper }
}

describe('library queries', () => {
  it('addresses a cover where the engine serves it, and none without one', () => {
    expect(coverUrl('co 1.jpg')).toBe('/api/v1/covers/co%201.jpg')
    expect(coverUrl(null)).toBeNull()
  })

  it('prepares every game once, with its system named', () => {
    const { world } = harness()
    const c = catalogue(world.games.slice(0, 2), world.systems)
    expect(c.systems.snes).toBe('Super Nintendo')
    expect(c.games.map((g) => g.sysLabel)).toEqual(['Super Nintendo', 'Game Boy Advance'])
    expect(c.games[0]?.hay).toContain('super nintendo')
  })

  it('reads the library and the systems together', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(() => useLibrary(), { wrapper })
    await waitFor(() => expect(result.current.data?.games).toHaveLength(40))
    expect(result.current.data?.systems.ps2).toBe('PlayStation 2')
  })

  it('reads one game only when one is open', async () => {
    const { wrapper } = harness()
    const none = renderHook(() => useGame(null), { wrapper })
    expect(none.result.current.fetchStatus).toBe('idle')
    const one = renderHook(() => useGame(3), { wrapper })
    await waitFor(() => expect(one.result.current.data?.summary).toContain('invented'))
  })

  it('starts a re-match as a job', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(() => useRematch(3), { wrapper })
    let job = ''
    await act(async () => {
      job = (await result.current.mutateAsync('igdb:42')).id
    })
    expect(job).toMatch(/^job-/)
  })
})
