import { composeStories } from '@storybook/react'
import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './AppHeader.stories'

const { Library } = composeStories(stories)

it('names the views in a main navigation, marks the current one, and links settings', () => {
  render(<Library />)
  const nav = screen.getByRole('navigation', { name: 'Main' })
  expect(
    within(nav)
      .getAllByRole('link')
      .map((a) => a.textContent),
  ).toEqual(['Library', 'Devices', 'System files'])
  expect(screen.getByRole('link', { name: 'Library' }).getAttribute('aria-current')).toBe('page')
  expect(screen.getByRole('link', { name: 'Settings' })).toBeTruthy()
  expect(screen.getByRole('searchbox')).toBeTruthy()
})
