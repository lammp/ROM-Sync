import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './ScreenshotStrip.stories'

const { Three, None } = composeStories(stories)

describe('ScreenshotStrip', () => {
  it('lists each screenshot as a button to open it', () => {
    render(<Three />)
    expect(screen.getByRole('list', { name: 'Screenshots of Super Metroid' })).toBeTruthy()
    expect(screen.getAllByRole('button')).toHaveLength(3)
  })

  it('draws nothing without screenshots', () => {
    render(<None />)
    expect(screen.queryByRole('list')).toBeNull()
    expect(screen.queryByRole('button')).toBeNull()
  })
})
