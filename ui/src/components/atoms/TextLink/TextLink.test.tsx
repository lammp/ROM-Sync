import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './TextLink.stories'

const { Route, External } = composeStories(stories)

describe('TextLink', () => {
  it('links to a route in place', () => {
    render(<Route />)
    const link = screen.getByRole('link', { name: 'Settings' })
    expect(link.getAttribute('href')).toMatch(/^\/settings\/?$/)
    expect(link.hasAttribute('target')).toBe(false)
  })

  it('opens the web apart, with no referrer', () => {
    render(<External />)
    const link = screen.getByRole('link', { name: 'IGDB' })
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toBe('noreferrer noopener')
  })
})
