import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './TagChipGroup.stories'

const { Default, GenresOnly } = composeStories(stories)

describe('TagChipGroup', () => {
  it('offers accept and reject on a suggestion, remove on an accepted tag, nothing on a genre', () => {
    render(<Default />)
    expect(screen.getByRole('button', { name: 'Reject Metroidvania' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Remove Science fiction' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Platform/ })).toBeNull()
  })

  it('reports a rejection', () => {
    render(<Default />)
    fireEvent.click(screen.getByRole('button', { name: 'Reject Metroidvania' }))
    expect(Default.args.onDecide).toHaveBeenCalledWith(Default.args.tags?.[2], false)
  })

  it('draws the genres alone', () => {
    render(<GenresOnly />)
    expect(screen.getByText('Adventure')).toBeTruthy()
    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })
})
