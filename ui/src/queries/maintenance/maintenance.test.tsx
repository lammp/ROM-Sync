import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { fakeFetch, freshWorld } from '../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../engine/engine'
import { ACTIONS, useMaintenanceReports, useRunMaintenance } from './maintenance'

function harness() {
  const engine = createEngine({
    fetch: fakeFetch(freshWorld()),
    baseUrl: 'http://engine.test',
    retry: 0,
  })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <EngineProvider engine={engine}>{children}</EngineProvider>
  )
  return { engine, wrapper }
}

describe('maintenance queries', () => {
  it('reads every action’s dry run in order', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(() => useMaintenanceReports(), { wrapper })
    await waitFor(() => expect(result.current.every((q) => q.isSuccess)).toBe(true))
    expect(result.current.map((q) => q.data?.action)).toEqual([...ACTIONS])
    expect(result.current.map((q) => q.data?.count)).toEqual([1, 0, 3, 0])
  })

  it('runs an action with the count its dry run found, then reads every dry run again', async () => {
    const { wrapper, engine } = harness()
    const { result } = renderHook(
      () => ({ reports: useMaintenanceReports(), run: useRunMaintenance() }),
      { wrapper },
    )
    await waitFor(() => expect(result.current.reports[2]?.data?.count).toBe(3))
    await act(async () => {
      expect(
        (await result.current.run.mutateAsync({ action: 'prune-covers', expected: 3 })).result,
      ).toEqual({ removed: 3 })
    })
    await waitFor(() => expect(result.current.reports[2]?.data?.count).toBe(0))
    expect(engine.client.getQueryState(['maintenance', 'compact'])?.dataUpdateCount).toBe(2)
  })
})
