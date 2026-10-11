import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './Divider.stories'

const { Default } = composeStories(stories)

it('is a separator', () => {
  render(<Default />)
  expect(screen.getByRole('separator').tagName).toBe('HR')
})
