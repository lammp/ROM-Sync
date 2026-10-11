import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './NoCover.stories'

const { Default } = composeStories(stories)

describe('NoCover', () => {
  it('shows the title in place of the art', () => {
    render(<Default />)
    expect(screen.getByText('Earthworm Jim 3D')).toBeTruthy()
  })
})
