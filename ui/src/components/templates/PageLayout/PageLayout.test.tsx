import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './PageLayout.stories'

const { WithActions } = composeStories(stories)

it('heads the page and carries its actions beside the heading, not in it', () => {
  render(<WithActions />)
  expect(screen.getByRole('heading', { level: 1, name: 'Devices' })).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Refresh' })).toBeTruthy()
  expect(screen.getByText('Two devices.')).toBeTruthy()
})
