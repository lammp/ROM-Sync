import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import * as stories from './SectionLabel.stories'

const { Default } = composeStories(stories)

it('renders its text', () => {
  render(<Default />)
  expect(screen.getByText('Needs files')).toBeTruthy()
})
