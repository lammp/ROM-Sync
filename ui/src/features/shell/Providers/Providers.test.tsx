import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './Providers.stories'

const { Default } = composeStories(stories)

it('gives the features beneath it an engine', () => {
  render(<Default />)
  expect(screen.getByText('engine polls every 1000 ms')).toBeTruthy()
})
