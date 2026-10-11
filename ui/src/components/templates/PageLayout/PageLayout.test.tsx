import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './PageLayout.stories'

const { WithActions } = composeStories(stories)

it('heads the page and carries its actions', () => {
  render(<WithActions />)
  expect(screen.getByRole('heading', { level: 1 }).textContent).toContain('Devices')
  expect(screen.getByRole('button', { name: 'Refresh' })).toBeTruthy()
  expect(screen.getByText('Two devices.')).toBeTruthy()
})
