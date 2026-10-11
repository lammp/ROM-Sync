import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Pill.stories'

const all = composeStories(stories)

describe('Pill', () => {
  it('renders each tone as inline text', () => {
    for (const [Story, text] of [
      [all.Neutral, 'queued'],
      [all.Ok, 'done'],
      [all.Warn, 'loose'],
      [all.Bad, 'failed'],
    ] as const) {
      const { unmount } = render(<Story />)
      expect(screen.getByText(text).tagName).toBe('SPAN')
      unmount()
    }
  })
})
