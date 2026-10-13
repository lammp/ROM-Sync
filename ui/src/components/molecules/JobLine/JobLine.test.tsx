import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { JobLine, summarise } from './JobLine'
import * as stories from './JobLine.stories'

const { Running, Done, Failed, Queued } = composeStories(stories)

describe('JobLine', () => {
  it('reads each state as a sentence', () => {
    const lines: [typeof Running, string][] = [
      [Running, 'scanning 412 of 8,214 · snes'],
      [Done, 'done: added 3, updated 2, removed 0'],
      [Failed, 'failed: The store folder is not set.'],
      [Queued, 'waiting to start…'],
    ]
    for (const [Story, text] of lines) {
      const { unmount } = render(<Story />)
      expect(screen.getByRole('status').textContent).toBe(text)
      unmount()
    }
  })

  it('never writes a result as JSON', () => {
    expect(summarise({ bytes_freed: 1024 })).toBe('bytes freed 1,024')
    expect(summarise(null)).toBe('nothing to do')
    render(<JobLine state="cancelling" />)
    expect(screen.getByRole('status').textContent).toBe('stopping…')
  })
})
