import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './NavButton.stories'

const { Default, Current } = composeStories(stories)

describe('NavButton', () => {
  it('is a link to its route', () => {
    render(<Default />)
    const link = screen.getByRole('link', { name: 'Devices' })
    expect(link.getAttribute('href')).toMatch(/^\/devices\/?$/)
    expect(link.hasAttribute('aria-current')).toBe(false)
  })

  it('marks the route on screen as the current page', () => {
    render(<Current />)
    expect(screen.getByRole('link').getAttribute('aria-current')).toBe('page')
  })
})
