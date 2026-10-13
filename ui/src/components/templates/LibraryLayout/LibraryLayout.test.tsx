import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './LibraryLayout.stories'

const { WithPanel } = composeStories(stories)

it('fills its three slots, each in a named region', () => {
  render(<WithPanel />)
  expect(screen.getByRole('complementary', { name: 'Filters' }).textContent).toBe('filters')
  expect(screen.getByRole('complementary', { name: 'Game details' }).textContent).toBe(
    'Super Metroid',
  )
  expect(screen.getByText('grid')).toBeTruthy()
})
