import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { fakeFetch, freshWorld } from '../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../engine/engine'
import {
  thresholds,
  useSettings,
  useTestCredentials,
  useWriteSettings,
  type Setting,
} from './settings'

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

  it('writes a section, refuses a value out of range with its field, and deletes with null', async () => {
    const engine = createEngine({
      fetch: fakeFetch(freshWorld()),
      baseUrl: 'http://engine.test',
      retry: 0,
    })
    const wrapper = ({ children }: { children: ReactNode }) => (
      <EngineProvider engine={engine}>{children}</EngineProvider>
    )
    const { result } = renderHook(() => ({ read: useSettings(), write: useWriteSettings() }), {
      wrapper,
    })
    await waitFor(() => expect(result.current.read.data).toBeDefined())
    await act(async () => {
      await result.current.write.mutateAsync({ 'device.probe_interval': 30, 'store.root': null })
    })
    const value = (k: string) => result.current.read.data?.find((s) => s.key === k)
    await waitFor(() =>
      expect(value('device.probe_interval')).toMatchObject({ value: 30, stored: true }),
    )
    expect(value('store.root')).toMatchObject({ value: '', stored: false })
    await expect(
      result.current.write.mutateAsync({ 'device.probe_interval': 1 }),
    ).rejects.toMatchObject({
      code: 'config.out_of_range',
      field: 'device.probe_interval',
    })
    expect(value('device.probe_interval')?.value).toBe(30)
  })

  it('keeps the secret out of every answer, and tests what is typed before it is saved', async () => {
    const engine = createEngine({
      fetch: fakeFetch(freshWorld()),
      baseUrl: 'http://engine.test',
      retry: 0,
    })
    const wrapper = ({ children }: { children: ReactNode }) => (
      <EngineProvider engine={engine}>{children}</EngineProvider>
    )
    const { result } = renderHook(
      () => ({ write: useWriteSettings(), test: useTestCredentials() }),
      { wrapper },
    )
    let saved: Setting[] = []
    await act(async () => {
      saved = await result.current.write.mutateAsync({
        'igdb.client_secret': 'a-secret-that-is-long-enough',
      })
    })
    const secret = saved.find((s) => s.key === 'igdb.client_secret')
    expect(secret).toMatchObject({ value: null, secret_state: { present: true, length: 28 } })
    expect(JSON.stringify(saved)).not.toContain('a-secret-that-is-long-enough')
    await act(async () => {
      expect(
        (await result.current.test.mutateAsync({ client_id: 'id', client_secret: 'short' }))
          .failed_at,
      ).toBe('token')
      expect((await result.current.test.mutateAsync({ client_id: 'id' })).ok).toBe(true)
    })
  })
})
