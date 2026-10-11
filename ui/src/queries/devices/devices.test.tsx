import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { CARD_REF, RETROID_REF, THOR_REF, fakeFetch, freshWorld } from '../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../engine/engine'
import {
  PROBE_MS,
  useAdopt,
  useCapacities,
  useCreateProfile,
  useInventories,
  useSelections,
  useAttached,
  useCapacity,
  useClearSelection,
  useInventory,
  usePlan,
  useProfiles,
  useRefreshCapacity,
  useSelection,
  useSetGames,
  useSetMode,
} from './devices'

function harness() {
  const world = freshWorld()
  const engine = createEngine({ fetch: fakeFetch(world), baseUrl: 'http://engine.test', retry: 0 })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <EngineProvider engine={engine}>{children}</EngineProvider>
  )
  return { world, engine, wrapper }
}

describe('device queries', () => {
  it('asks for attached devices at version 1’s probe interval', async () => {
    expect(PROBE_MS).toBe(15_000)
    const { wrapper } = harness()
    const { result } = renderHook(() => useAttached(), { wrapper })
    await waitFor(() => expect(result.current.data?.devices[0]?.profile?.name).toBe('Thor'))
  })

  it('reads profiles, and for one profile its selection and inventory', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(
      () => ({
        profiles: useProfiles(),
        selection: useSelection('dev-1'),
        inventory: useInventory('dev-1'),
      }),
      { wrapper },
    )
    await waitFor(() => expect(result.current.inventory.data).toHaveLength(2))
    expect(result.current.profiles.data?.map((p) => p.name)).toEqual(['Deck card', 'Thor'])
    expect(result.current.selection.data?.modes).toEqual({ snes: 'all', gba: 'none' })
  })

  it('asks for nothing about a device not chosen or not attached', () => {
    const { wrapper } = harness()
    const { result } = renderHook(
      () => [useSelection(null), useInventory(null), usePlan(null), useCapacity(null)],
      { wrapper },
    )
    expect(result.current.map((q) => q.fetchStatus)).toEqual(['idle', 'idle', 'idle', 'idle'])
  })

  it('reads the plan and the capacity of an attached device', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(() => ({ plan: usePlan(THOR_REF), cap: useCapacity(THOR_REF) }), {
      wrapper,
    })
    await waitFor(() => expect(result.current.plan.data?.bytes.fits).toBe(true))
    expect(result.current.cap.data?.total).toBeGreaterThan(0)
  })

  it('changes the selection through the engine, holding its answer', async () => {
    const { wrapper, engine } = harness()
    engine.client.setQueryData(['plan', THOR_REF], { stale: true })
    const { result } = renderHook(
      () => ({
        selection: useSelection('dev-1'),
        games: useSetGames('dev-1'),
        mode: useSetMode('dev-1'),
        clear: useClearSelection('dev-1'),
      }),
      { wrapper },
    )
    await waitFor(() => expect(result.current.selection.data).toBeDefined())
    await act(() => result.current.games.mutateAsync({ gameIds: [1], include: false }))
    await waitFor(() =>
      expect(result.current.selection.data?.overrides).toEqual({ '1': false, '2': true }),
    )
    expect(engine.client.getQueryState(['plan', THOR_REF])?.isInvalidated).toBe(false)
    await act(() => result.current.mode.mutateAsync({ system: 'gba', mode: 'all' }))
    await waitFor(() => expect(result.current.selection.data?.modes.gba).toBe('all'))
    expect(result.current.selection.data?.overrides).toEqual({ '1': false })
    await act(() => result.current.clear.mutateAsync())
    await waitFor(() =>
      expect(result.current.selection.data).toMatchObject({
        modes: { snes: 'none', gba: 'none' },
        overrides: {},
      }),
    )
  })

  it('reads the plan and the space again when the summary says the selection settled', () => {
    const { wrapper, engine } = harness()
    engine.client.setQueryData(['plan', THOR_REF], { stale: true })
    engine.client.setQueryData(['capacity', THOR_REF], { stale: true })
    const none = renderHook(() => useRefreshCapacity(null), { wrapper })
    none.result.current()
    expect(engine.client.getQueryState(['plan', THOR_REF])?.isInvalidated).toBe(false)
    const { result, rerender } = renderHook(() => useRefreshCapacity(THOR_REF), { wrapper })
    const first = result.current
    rerender()
    expect(result.current).toBe(first)
    result.current()
    expect(engine.client.getQueryState(['plan', THOR_REF])?.isInvalidated).toBe(true)
    expect(engine.client.getQueryState(['capacity', THOR_REF])?.isInvalidated).toBe(true)
  })

  it('reads every profile’s selection and contents, and every attached device’s space, in order', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(
      () => ({
        selections: useSelections(['dev-1', 'dev-2']),
        inventories: useInventories(['dev-1', 'dev-2']),
        space: useCapacities([THOR_REF, CARD_REF]),
      }),
      { wrapper },
    )
    await waitFor(() => expect(result.current.space.every((q) => q.isSuccess)).toBe(true))
    await waitFor(() => expect(result.current.inventories.every((q) => q.isSuccess)).toBe(true))
    expect(result.current.selections.map((q) => q.data?.device_id)).toEqual(['dev-1', 'dev-2'])
    expect(result.current.inventories.map((q) => q.data?.length)).toEqual([2, 0])
    expect(result.current.space[1]?.data?.free).toBeGreaterThan(
      result.current.space[0]?.data?.free ?? 0,
    )
  })

  it('makes a profile and adopts another computer’s, then reads devices and profiles again', async () => {
    const { wrapper, engine } = harness()
    engine.client.setQueryData(['devices'], { stale: true })
    engine.client.setQueryData(['profiles'], [])
    const { result } = renderHook(() => ({ create: useCreateProfile(), adopt: useAdopt() }), {
      wrapper,
    })
    let made = ''
    await act(async () => {
      made = (
        await result.current.create.mutateAsync({ ref: CARD_REF, name: 'Card', writeMarker: true })
      ).id
    })
    expect(made).toBe('dev-3')
    expect(engine.client.getQueryState(['devices'])?.isInvalidated).toBe(true)
    expect(engine.client.getQueryState(['profiles'])?.isInvalidated).toBe(true)
    let adopted = ''
    await act(async () => {
      adopted = (await result.current.adopt.mutateAsync(RETROID_REF)).id
    })
    expect(adopted).toBe('dev-elsewhere')
  })

  it('carries the engine’s refusal to adopt a device with no marker', async () => {
    const { wrapper } = harness()
    const { result } = renderHook(() => useAdopt(), { wrapper })
    await expect(result.current.mutateAsync(CARD_REF)).rejects.toMatchObject({
      code: 'dest.marker_untrusted',
    })
  })
})
