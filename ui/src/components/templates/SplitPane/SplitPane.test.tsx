import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './SplitPane.stories'

const { Default } = composeStories(stories)

it('puts the list in a named navigation beside the detail', () => {
  render(<Default />)
  expect(screen.getByRole('navigation', { name: 'Systems' }).textContent).toBe('PlayStation')
  expect(screen.getByText('BIOS files')).toBeTruthy()
})
