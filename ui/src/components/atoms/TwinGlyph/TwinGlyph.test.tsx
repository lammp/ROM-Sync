import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './TwinGlyph.stories'

const { Twin, Duplicate } = composeStories(stories)

describe('TwinGlyph', () => {
  it('is named for what it marks, not by its glyph', () => {
    render(<Twin />)
    expect(screen.getByRole('img', { name: 'Also on 2 other systems' })).toBeTruthy()
    expect(screen.getByText('⇄').getAttribute('aria-hidden')).toBe('true')
  })

  it('names a duplicate', () => {
    render(<Duplicate />)
    expect(screen.getByRole('img', { name: 'In the library twice on this system' })).toBeTruthy()
  })
})
