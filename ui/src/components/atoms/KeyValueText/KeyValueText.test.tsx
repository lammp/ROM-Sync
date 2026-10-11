import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './KeyValueText.stories'

const { Path } = composeStories(stories)

it('renders its text as a block', () => {
  render(<Path />)
  expect(screen.getByText(/Super Metroid/).tagName).toBe('DIV')
})
