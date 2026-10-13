import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SearchInput.stories'

const { Empty, WithQuery } = composeStories(stories)

describe('SearchInput', () => {
  it('is a labelled search box', () => {
    render(<Empty />)
    expect(screen.getByRole('searchbox', { name: 'Search the library' })).toBeTruthy()
  })

  it('shows the query and reports edits', () => {
    render(<WithQuery />)
    const box = screen.getByRole('searchbox') as HTMLInputElement
    expect(box.value).toBe('system:snes rating>=80')
    fireEvent.change(box, { target: { value: '' } })
    expect(WithQuery.args.onChange).toHaveBeenCalledWith('')
  })
})
