import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { fakeFetch, freshWorld } from '../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../engine/engine'
import { LIBRARY_KEY } from '../library/library'
import { useTagChange, useTags } from './tags'

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

describe('tag queries', () => {
  it('reads a game’s tags only when a game is open', async () => {
    const { wrapper } = harness()
    expect(renderHook(() => useTags(null), { wrapper }).result.current.fetchStatus).toBe('idle')
    const { result } = renderHook(() => useTags(1), { wrapper })
    await waitFor(() =>
      expect(result.current.data?.tags.map((t) => t.tag)).toEqual(['Star', 'Space opera']),
    )
  })

  it('adds, decides and removes, each answered with the game’s tags, and reads the library again', async () => {
    const { wrapper, engine } = harness()
    engine.client.setQueryData(LIBRARY_KEY, { games: [], systems: {} })
    const { result } = renderHook(() => ({ tags: useTags(1), change: useTagChange(1) }), {
      wrapper,
    })
    await waitFor(() => expect(result.current.tags.data).toBeDefined())
    await act(() => result.current.change.mutateAsync({ op: 'add', tag: 'Co-op', kind: 'mode' }))
    await waitFor(() => expect(result.current.tags.data?.tags.map((t) => t.tag)).toContain('Co-op'))
    expect(engine.client.getQueryState(LIBRARY_KEY)?.isInvalidated).toBe(true)
    await act(() =>
      result.current.change.mutateAsync({
        op: 'decide',
        tag: 'Space opera',
        kind: 'theme',
        accept: false,
      }),
    )
    await waitFor(() =>
      expect(result.current.tags.data?.tags.find((t) => t.tag === 'Space opera')?.state).toBe(
        'rejected',
      ),
    )
    await act(() => result.current.change.mutateAsync({ op: 'remove', tag: 'Co-op', kind: 'mode' }))
    await waitFor(() =>
      expect(result.current.tags.data?.tags.map((t) => t.tag)).toEqual(['Star', 'Space opera']),
    )
  })
})
