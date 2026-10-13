import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { SORTS } from '../../../lib/sort/sort'
import * as stories from './SortControl.stories'

const { Default } = composeStories(stories)

it('offers exactly the six orders lib/sort knows', () => {
  render(<Default />)
  expect(screen.getAllByRole('option').map((o) => (o as HTMLOptionElement).value)).toEqual([
    ...SORTS,
  ])
})
