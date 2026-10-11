import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './ActiveChipList.stories'

const { Some, None } = composeStories(stories)

describe('ActiveChipList', () => {
  it('names each filter and lets it go alone', () => {
    render(<Some />)
    expect(screen.getByRole('group', { name: 'Filters in force' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Remove Super Nintendo' }))
    expect(Some.args.filters?.[0]?.onRemove).toHaveBeenCalled()
  })

  it('draws nothing with no filters', () => {
    const { container } = render(<None />)
    expect(container.textContent).toBe('')
  })
})
