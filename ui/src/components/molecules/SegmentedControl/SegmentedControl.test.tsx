import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SegmentedControl.stories'

const { Default } = composeStories(stories)

describe('SegmentedControl', () => {
  it('is a named radio group with one checked', () => {
    render(<Default />)
    expect(screen.getByRole('radiogroup', { name: 'Rule for Super Nintendo' })).toBeTruthy()
    expect(screen.getAllByRole('radio').map((r) => r.getAttribute('aria-checked'))).toEqual([
      'true',
      'false',
      'false',
    ])
  })

  it('reports a new choice, not the one already made', () => {
    render(<Default />)
    fireEvent.click(screen.getByRole('radio', { name: 'All' }))
    expect(Default.args.onChange).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('radio', { name: 'Off' }))
    expect(Default.args.onChange).toHaveBeenCalledWith('off')
  })
})
