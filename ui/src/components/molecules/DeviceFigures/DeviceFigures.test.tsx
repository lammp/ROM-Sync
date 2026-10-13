import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './DeviceFigures.stories'

const { Default } = composeStories(stories)

it('pairs each figure with its name', () => {
  render(<Default />)
  expect(screen.getAllByRole('term').map((t) => t.textContent)).toEqual([
    'selected',
    'on device',
    'used by games',
  ])
  expect(screen.getAllByRole('definition').map((d) => d.textContent)).toEqual([
    '1,284',
    '1,190',
    '96.0 GB',
  ])
})
