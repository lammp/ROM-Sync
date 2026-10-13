import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SMART_LISTS } from './SmartListButton'
import * as stories from './SmartListButton.stories'

const { TopRated } = composeStories(stories)

describe('SmartListButton', () => {
  it('puts its query in the search', () => {
    render(<TopRated />)
    fireEvent.click(screen.getByRole('button', { name: 'Top rated' }))
    expect(TopRated.args.onApply).toHaveBeenCalledWith('rating>85 votes>50')
  })

  it('carries version 1s six lists', () => {
    expect(SMART_LISTS.map((s) => s.label)).toEqual([
      'Top rated',
      'Modern',
      'Retro',
      'Big games',
      'RPGs',
      'Platformers',
    ])
  })
})
