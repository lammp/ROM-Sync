import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './StatRow.stories'

const { Default } = composeStories(stories)

it('pairs a term with its figure', () => {
  render(<Default />)
  expect(screen.getByRole('term').textContent).toBe('Games')
  expect(screen.getByRole('definition').textContent).toBe('8,214')
})
