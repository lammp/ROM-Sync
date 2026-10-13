import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Lamp.stories'

const { Off, On, Trouble } = composeStories(stories)

describe('Lamp', () => {
  it('names each state', () => {
    for (const [Story, name] of [
      [Off, 'Not connected'],
      [On, 'Connected'],
      [Trouble, 'Device not writable'],
    ] as const) {
      const { unmount } = render(<Story />)
      expect(screen.getByRole('img', { name })).toBeTruthy()
      unmount()
    }
  })
})
