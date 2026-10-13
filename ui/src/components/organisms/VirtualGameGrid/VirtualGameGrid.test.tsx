import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './VirtualGameGrid.stories'

const { WindowMatchesFixture, Empty } = composeStories(stories)

describe('VirtualGameGrid', () => {
  it('is a named region that renders a window, not every item', () => {
    render(<WindowMatchesFixture />)
    expect(screen.getByRole('region', { name: 'Games' })).toBeTruthy()
    const shown = screen.getAllByRole('listitem').length
    expect(shown).toBeGreaterThan(0)
    expect(shown).toBeLessThan(1000)
  })

  it('says when nothing matches', () => {
    render(<Empty />)
    expect(screen.getByText('Nothing matches these filters.')).toBeTruthy()
    expect(screen.queryByRole('list')).toBeNull()
  })
})
