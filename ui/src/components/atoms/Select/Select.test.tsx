import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './Select.stories'

const { Default, Chip } = composeStories(stories)

describe('Select', () => {
  it('is named by its label and shows the chosen option', () => {
    render(<Default />)
    expect((screen.getByRole('combobox', { name: 'Sort' }) as HTMLSelectElement).value).toBe(
      'title',
    )
    expect(screen.getAllByRole('option').map((o) => o.textContent)).toEqual([
      'Title',
      'Year',
      'Rating',
    ])
  })

  it('reports the option chosen', () => {
    render(<Default />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'rating' } })
    expect(Default.args.onChange).toHaveBeenCalledWith('rating')
  })

  it('keeps a hidden label announced', () => {
    render(<Chip />)
    expect(screen.getByRole('combobox', { name: 'Version' })).toBeTruthy()
  })
})
