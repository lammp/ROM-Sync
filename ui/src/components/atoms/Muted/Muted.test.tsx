import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import * as stories from './Muted.stories'

const { Default } = composeStories(stories)

test('renders its text as secondary text', () => {
  render(<Default />)
  expect(screen.getByText('1,284 games').tagName).toBe('SPAN')
})
