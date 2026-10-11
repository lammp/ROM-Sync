import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './FacetSection.stories'

const { Open, Collapsed, WithChosen, MorePastTheFold, Unfolded } = composeStories(stories)

describe('FacetSection', () => {
  it('is a disclosure: the heading button controls the body', () => {
    render(<Open />)
    const toggle = screen.getByRole('button', { name: 'System' })
    const body = document.getElementById(toggle.getAttribute('aria-controls') ?? '')
    expect(body?.hidden).toBe(false)
    expect(screen.getByRole('heading', { name: 'System' })).toBeTruthy()
  })

  it('collapse_persists: the state comes from outside and every toggle is reported', () => {
    const { rerender } = render(<Open />)
    fireEvent.click(screen.getByRole('button', { name: 'System' }))
    expect(Open.args.onCollapsedChange).toHaveBeenCalledWith(true)
    expect(screen.getByRole('button', { name: 'System' }).getAttribute('aria-expanded')).toBe(
      'true',
    )
    rerender(<Collapsed />)
    const toggle = screen.getByRole('button', { name: 'System' })
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(document.getElementById(toggle.getAttribute('aria-controls') ?? '')?.hidden).toBe(true)
    fireEvent.click(toggle)
    expect(Collapsed.args.onCollapsedChange).toHaveBeenCalledWith(false)
  })

  it('says how many are chosen and offers to clear them, only then', () => {
    render(<WithChosen />)
    expect(screen.getByText('2 chosen')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Clear System' }))
    expect(WithChosen.args.onClear).toHaveBeenCalled()
  })

  it('offers no clear with nothing chosen', () => {
    render(<Open />)
    expect(screen.queryByRole('button', { name: /^Clear/ })).toBeNull()
  })

  it('offers more with the hidden count, and less once unfolded', () => {
    const { unmount } = render(<MorePastTheFold />)
    expect(screen.getByRole('button', { name: 'more… (+4)' })).toBeTruthy()
    unmount()
    render(<Unfolded />)
    expect(screen.getByRole('button', { name: 'less…' })).toBeTruthy()
  })
})
