import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { fakeFetch, freshWorld } from '../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../engine/engine'
import { thresholds, useSettings, type Setting } from './settings'

const item = (key: string, value: unknown) => ({ key, value }) as Setting

describe('settings queries', () => {
  it('takes the meter thresholds from the registry', () => {
    expect(
      thresholds([
        item('capacity.warn_fraction', 0.7),
        item('capacity.alarm_fraction', 0.95),
        item('plan.free_space_margin', 1024),
      ]),
    ).toEqual({ warnFraction: 0.7, alarmFraction: 0.95, margin: 1024 })
  })

  it("uses the registry's defaults until the settings are read, or for a value of the wrong kind", () => {
    const defaults = { warnFraction: 0.8, alarmFraction: 0.9, margin: 512 * 1024 * 1024 }
    expect(thresholds(undefined)).toEqual(defaults)
    expect(thresholds([item('capacity.warn_fraction', 'high')])).toEqual(defaults)
  })

  it('reads the settings', async () => {
    const engine = createEngine({
      fetch: fakeFetch(freshWorld()),
      baseUrl: 'http://engine.test',
      retry: 0,
    })
    const wrapper = ({ children }: { children: ReactNode }) => (
      <EngineProvider engine={engine}>{children}</EngineProvider>
    )
    const { result } = renderHook(() => useSettings(), { wrapper })
    await waitFor(() => expect(result.current.data?.map((s) => s.key)).toContain('store.root'))
  })
})
