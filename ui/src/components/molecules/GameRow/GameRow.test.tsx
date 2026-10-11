import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './GameRow.stories'

const { Plain, Current, AllFourBadges } = composeStories(stories)

describe('GameRow', () => {
  it('shows the system, year, rating and size in columns', () => {
    render(<Plain />)
    for (const text of ['Super Nintendo', '1994', '93', '3.00 MB'])
      expect(screen.getByText(text)).toBeTruthy()
  })

  it('opens the game from its title', () => {
    render(<Plain />)
    fireEvent.click(screen.getByRole('button', { name: 'Super Metroid' }))
    expect(Plain.args.onOpen).toHaveBeenCalled()
  })

  it('marks the current game', () => {
    render(<Current />)
    expect(screen.getByRole('button', { name: 'Super Metroid' }).getAttribute('aria-current')).toBe(
      'true',
    )
  })

  it('carries the same four badges as a tile', () => {
    render(<AllFourBadges />)
    expect(
      screen.getByRole('button', { name: /for Thor: not selected, chosen by hand/ }),
    ).toBeTruthy()
    expect(screen.getByText('on device')).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Also on 1 other system: gba' })).toBeTruthy()
  })
})
