import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './AppShell.stories'

const { Default } = composeStories(stories)

describe('AppShell', () => {
  it('lays out the header and main landmarks with the hosts after them', () => {
    render(<Default />)
    expect(screen.getByRole('banner')).toBeTruthy()
    const main = screen.getByRole('main')
    expect(main.id).toBe('main')
    expect(screen.getByRole('link', { name: 'Skip to content' }).getAttribute('href')).toBe('#main')
    expect(screen.getByRole('status')).toBeTruthy()
  })
})
