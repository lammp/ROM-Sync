import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './CoverImage.stories'

const { Tile } = composeStories(stories)

describe('CoverImage', () => {
  it('is named by the title and loads lazily, decoding off the main thread', () => {
    render(<Tile />)
    const img = screen.getByRole('img', { name: 'Super Metroid' })
    expect(img.getAttribute('loading')).toBe('lazy')
    expect(img.getAttribute('decoding')).toBe('async')
  })
})
