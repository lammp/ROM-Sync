import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { THOR_REF, fakeFetch, freshWorld, seed } from '../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../engine/engine'
import { useAfterRecover, useRecover, useRecoverLists } from './recover'

function harness(recover = true) {
  const world = freshWorld()
  if (recover) seed(world, 'recover')
  const engine = createEngine({ fetch: fakeFetch(world), baseUrl: 'http://engine.test', retry: 0 })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <EngineProvider engine={engine}>{children}</EngineProvider>
  )
  return { world, engine, wrapper }
}

describe('recover queries', () => {
  it('lists what each device holds that the library lacks, and nothing for a device that holds none', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(() => useRecoverLists([THOR_REF]), { wrapper })
    await waitFor(() => expect(result.current[0]?.data).toHaveLength(4))
    expect(result.current[0]?.data?.map((i) => i.name)).toEqual([
      'Hidden Gem (USA).sfc',
      'Clash (USA).sfc',
      'Translation Patch',
      'Homebrew.nes',
    ])
    const empty = harness(false)
    const none = renderHook(() => useRecoverLists([THOR_REF]), { wrapper: empty.wrapper })
    await waitFor(() => expect(none.result.current[0]?.data).toEqual([]))
  })

  it('recovers one item as a job, and fails one whose name the store already has', async () => {
    const { wrapper, world } = harness()
    const { result } = renderHook(() => useRecover(THOR_REF), { wrapper })
    await act(async () => {
      const placed = await result.current.mutateAsync({
        system: 'snes',
        name: 'Hidden Gem (USA).sfc',
      })
      expect([placed.state, placed.result]).toEqual(['done', { placed: 1, bytes: 2 * 1024 * 1024 }])
      const clash = await result.current.mutateAsync({ system: 'snes', name: 'Clash (USA).sfc' })
      expect([clash.state, clash.error_code]).toEqual(['failed', 'store.would_overwrite'])
    })
    expect(world.unread.map((u) => u.name)).toEqual(['Clash (USA).sfc', 'Hidden Gem (USA).sfc'])
  })

  it('reads every list and the library again after', () => {
    const { wrapper, engine } = harness()
    const keys = [['recover', THOR_REF], ['library'], ['systems']]
    for (const k of keys) engine.client.setQueryData(k, { stale: true })
    renderHook(() => useAfterRecover(), { wrapper }).result.current()
    expect(keys.map((k) => engine.client.getQueryState(k)?.isInvalidated)).toEqual([
      true,
      true,
      true,
    ])
  })
})
