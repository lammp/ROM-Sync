import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './LibraryToolbar.stories'

const { Grid, List } = composeStories(stories)

describe('LibraryToolbar', () => {
  it('says how many games show, with their size', () => {
    render(<Grid />)
    expect(screen.getByRole('status').textContent).toBe('245 of 8,214 · 3.00 GB')
    expect(screen.getByRole('toolbar', { name: 'Library' })).toBeTruthy()
  })

  it('offers the tile size only in the grid', () => {
    const { unmount } = render(<Grid />)
    expect(screen.getByRole('slider', { name: 'Tiles' })).toBeTruthy()
    unmount()
    render(<List />)
    expect(screen.queryByRole('slider')).toBeNull()
  })
})
