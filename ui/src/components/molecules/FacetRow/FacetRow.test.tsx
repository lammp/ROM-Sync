import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './FacetRow.stories'

const { Default, Chosen, ChosenAtZero } = composeStories(stories)

describe('FacetRow', () => {
  it('is a toggle named by its value and count', () => {
    render(<Default />)
    const row = screen.getByRole('button', { name: /Super Nintendo\s*412/ })
    expect(row.getAttribute('aria-pressed')).toBe('false')
    fireEvent.click(row)
    expect(Default.args.onToggle).toHaveBeenCalled()
  })

  it('is pressed when chosen, even at zero', () => {
    for (const Story of [Chosen, ChosenAtZero]) {
      const { unmount } = render(<Story />)
      expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe('true')
      unmount()
    }
  })
})
