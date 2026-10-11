import { composeStories } from '@storybook/react'
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Chevron.stories'

const { Expanded, Collapsed } = composeStories(stories)

describe('Chevron', () => {
  it('is hidden from assistive technology in both states', () => {
    for (const Story of [Expanded, Collapsed]) {
      const { container, unmount } = render(<Story />)
      expect(container.firstElementChild?.getAttribute('aria-hidden')).toBe('true')
      unmount()
    }
  })
})
