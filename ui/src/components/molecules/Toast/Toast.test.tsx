import { composeStories } from '@storybook/react'
import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TOAST_MS } from './Toast'
import * as stories from './Toast.stories'

const { Info, Problem, Empty } = composeStories(stories)

afterEach(() => {
  vi.useRealTimers()
})

describe('Toast', () => {
  it('keeps its live region in the page even with nothing to say', () => {
    render(<Empty />)
    const region = screen.getByRole('status')
    expect(region.getAttribute('aria-live')).toBe('polite')
    expect(region.textContent).toBe('')
  })

  it('says a problem in words', () => {
    render(<Problem />)
    expect(screen.getByRole('status').textContent).toContain('Problem: ')
  })

  it('goes after version 1s times, errors staying longer', () => {
    vi.useFakeTimers()
    render(<Info />)
    act(() => {
      vi.advanceTimersByTime(TOAST_MS.info - 1)
    })
    expect(Info.args.onDismiss).not.toHaveBeenCalled()
    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(Info.args.onDismiss).toHaveBeenCalledWith(1)
    expect(TOAST_MS).toEqual({ info: 2500, bad: 6000 })
  })
})
