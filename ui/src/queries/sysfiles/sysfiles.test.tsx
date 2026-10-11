import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { THOR_REF, fakeFetch, freshWorld } from '../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../engine/engine'
import {
  useAfterSysfiles,
  useRemoveOther,
  useStage,
  useStoreSysfiles,
  useSurvey,
  useSysReport,
  useUnstage,
} from './sysfiles'

function harness() {
  const world = freshWorld()
  const engine = createEngine({ fetch: fakeFetch(world), baseUrl: 'http://engine.test', retry: 0 })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <EngineProvider engine={engine}>{children}</EngineProvider>
  )
  return { world, engine, wrapper }
}

describe('system files queries', () => {
  it('reads the store’s copies with no device', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(() => useStoreSysfiles(), { wrapper })
    await waitFor(() =>
      expect(result.current.data?.map((i) => i.name)).toEqual(['gba_bios.bin', 'scph39001.bin']),
    )
  })

  it('reads a device’s report only when one is plugged in', async () => {
    const { wrapper } = harness()
    const none = renderHook(() => useSysReport(null), { wrapper })
    expect(none.result.current.fetchStatus).toBe('idle')
    const { result } = renderHook(() => useSysReport(THOR_REF), { wrapper })
    await waitFor(() => expect(result.current.data?.surveyed_at).toBeNull())
    expect(result.current.data?.systems.map((s) => s.readiness)).toEqual([
      'unknown',
      'unknown',
      'none',
      'none',
    ])
  })

  it('surveys, stages, unstages and removes a stray item, each as a job on the device', async () => {
    const { wrapper, world } = harness()
    const { result } = renderHook(
      () => ({
        survey: useSurvey(THOR_REF),
        stage: useStage(THOR_REF),
        unstage: useUnstage(THOR_REF),
        other: useRemoveOther(THOR_REF),
      }),
      { wrapper },
    )
    await act(async () => {
      expect((await result.current.survey.mutateAsync()).result).toEqual({ entries: 12 })
      expect((await result.current.stage.mutateAsync('gba')).result).toEqual({ placed: 1 })
      expect((await result.current.unstage.mutateAsync('gba')).result).toEqual({ removed: 1 })
      await result.current.other.mutateAsync({ path: 'ROM-Sync/bios/gba', name: 'old_bios.bin' })
    })
    expect(world.sysfiles[THOR_REF]).toMatchObject({ staged: { gba: false }, others: [] })
  })

  it('reads the report again once a job ends, and nothing without a device', () => {
    const { wrapper, engine } = harness()
    engine.client.setQueryData(['sysfiles', THOR_REF], { stale: true })
    renderHook(() => useAfterSysfiles(null), { wrapper }).result.current()
    expect(engine.client.getQueryState(['sysfiles', THOR_REF])?.isInvalidated).toBe(false)
    renderHook(() => useAfterSysfiles(THOR_REF), { wrapper }).result.current()
    expect(engine.client.getQueryState(['sysfiles', THOR_REF])?.isInvalidated).toBe(true)
  })
})
