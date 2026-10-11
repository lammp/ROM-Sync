import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SelectionBadge.stories'

const { NotSelected, Selected, SelectedByHand, ExcludedByHand } = composeStories(stories)

describe('SelectionBadge', () => {
  it('says each of its four states in words, not only in colour', () => {
    const named: [typeof NotSelected, string][] = [
      [NotSelected, 'not selected'],
      [Selected, 'selected'],
      [SelectedByHand, 'selected, chosen by hand'],
      [ExcludedByHand, 'not selected, chosen by hand'],
    ]
    for (const [Story, state] of named) {
      const { unmount } = render(<Story />)
      expect(screen.getByRole('button', { name: `Super Metroid for Thor: ${state}` })).toBeTruthy()
      unmount()
    }
  })

  it('is a toggle that does not open the tile beneath it', () => {
    let opened = false
    render(
      <div onClick={() => (opened = true)} role="presentation">
        <NotSelected />
      </div>,
    )
    fireEvent.click(screen.getByRole('button'))
    expect(NotSelected.args.onToggle).toHaveBeenCalled()
    expect(opened).toBe(false)
  })

  it('shows a tick when selected', () => {
    render(<Selected />)
    expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByText('✓')).toBeTruthy()
  })
})
