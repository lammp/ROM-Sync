import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './CardGrid.stories'

const { Wide } = composeStories(stories)

it('is a named list of cards at the minimum width asked for', () => {
  render(<Wide />)
  const list = screen.getByRole('list', { name: 'Settings' })
  expect(list.style.getPropertyValue('--card-min')).toBe('360px')
  expect(screen.getAllByRole('listitem')).toHaveLength(2)
})
