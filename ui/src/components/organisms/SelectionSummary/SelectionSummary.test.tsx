import { composeStories } from '@storybook/react'
import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CAPACITY_SETTLE_MS } from './SelectionSummary'
import * as stories from './SelectionSummary.stories'

const { Default, NothingSelected } = composeStories(stories)

afterEach(() => {
  vi.useRealTimers()
})

describe('SelectionSummary', () => {
  it('counts what is selected and on the device, and names the bulk actions with their counts', () => {
    render(<Default />)
    expect(screen.getByRole('group', { name: 'Selection for Thor' }).textContent).toContain(
      '1,284 selected (96.0 GB)',
    )
    expect(screen.getByText('1,190 on device')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Clear shown (214)' })).toBeTruthy()
  })

  it('holds the actions that would do nothing', () => {
    render(<NothingSelected />)
    expect(
      (screen.getByRole('button', { name: 'Clear shown' }) as HTMLButtonElement).disabled,
    ).toBe(true)
    expect((screen.getByRole('button', { name: 'Clear all' }) as HTMLButtonElement).disabled).toBe(
      true,
    )
  })

  it('reads the capacity once the selection has been still for 250 ms', () => {
    vi.useFakeTimers()
    const { rerender } = render(<Default selectionKey={1} />)
    act(() => vi.advanceTimersByTime(CAPACITY_SETTLE_MS - 50))
    rerender(<Default selectionKey={2} />)
    act(() => vi.advanceTimersByTime(CAPACITY_SETTLE_MS - 50))
    rerender(<Default selectionKey={3} />)
    expect(Default.args.onSettled).not.toHaveBeenCalled()
    act(() => vi.advanceTimersByTime(CAPACITY_SETTLE_MS))
    expect(Default.args.onSettled).toHaveBeenCalledOnce()
  })
})
