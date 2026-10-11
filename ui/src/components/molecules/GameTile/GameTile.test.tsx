import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './GameTile.stories'

const { NoDevice, WithCover, Current, AllFourBadges, DuplicateSelected } = composeStories(stories)

describe('GameTile', () => {
  it('opens the game from a button named by its title and caption', () => {
    render(<NoDevice />)
    const open = screen.getByRole('button', { name: /^Super Metroid/ })
    expect(open.textContent).toContain('snes')
    expect(open.textContent).toContain('1994 · 93')
    fireEvent.click(open)
    expect(NoDevice.args.onOpen).toHaveBeenCalled()
  })

  it('draws the title in place of a missing cover, and the cover when there is one', () => {
    const { unmount } = render(<NoDevice />)
    expect(screen.getAllByText('Super Metroid')).toHaveLength(2)
    unmount()
    const { container } = render(<WithCover />)
    expect(container.querySelector('img')?.getAttribute('alt')).toBe('')
  })

  it('marks the game the detail panel shows', () => {
    render(<Current />)
    expect(
      screen.getByRole('button', { name: /^Super Metroid/ }).getAttribute('aria-current'),
    ).toBe('true')
  })

  it('carries all four badges, each in words', () => {
    render(<AllFourBadges />)
    expect(
      screen.getByRole('button', { name: 'Super Metroid for Thor: selected, chosen by hand' }),
    ).toBeTruthy()
    expect(screen.getByText('on device')).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Also on 1 other system: gba' })).toBeTruthy()
    expect(
      screen
        .getByRole('button', { name: /^Super Metroid\s*snes\s*1994 · 93$/ })
        .getAttribute('aria-current'),
    ).toBe('true')
  })

  it('toggles selection without opening the game', () => {
    render(<AllFourBadges />)
    fireEvent.click(screen.getByRole('button', { name: /for Thor/ }))
    expect(AllFourBadges.args.device?.onToggle).toHaveBeenCalled()
    expect(AllFourBadges.args.onOpen).not.toHaveBeenCalled()
  })

  it('names a duplicate selection', () => {
    render(<DuplicateSelected />)
    expect(screen.getByRole('img', { name: 'Already selected on gba' })).toBeTruthy()
    expect(screen.queryByText('on device')).toBeNull()
  })
})
