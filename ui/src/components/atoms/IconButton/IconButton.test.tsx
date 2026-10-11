import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './IconButton.stories'

const { Settings, Close } = composeStories(stories)

describe('IconButton', () => {
  it('takes its accessible name from the label, not the glyph', () => {
    render(<Close />)
    expect(screen.getByRole('button', { name: 'Close details' })).toBeTruthy()
    expect(screen.getByText('×').getAttribute('aria-hidden')).toBe('true')
  })

  it('shows the label as a tooltip too', () => {
    render(<Settings />)
    expect(screen.getByRole('button').getAttribute('title')).toBe('Settings')
  })
})
