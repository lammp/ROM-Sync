import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './ActionLink.stories'

const { Default } = composeStories(stories)

describe('ActionLink', () => {
  it('is a button, not a span', () => {
    render(<Default />)
    const button = screen.getByRole('button', { name: 'Show 50 more' })
    expect(button.getAttribute('type')).toBe('button')
    fireEvent.click(button)
    expect(Default.args.onClick).toHaveBeenCalled()
  })
})
