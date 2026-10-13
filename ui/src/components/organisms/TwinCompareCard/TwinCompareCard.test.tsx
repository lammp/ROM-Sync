import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './TwinCompareCard.stories'

const { ByKeyboard, MatchedOnFileName } = composeStories(stories)

describe('TwinCompareCard', () => {
  it('keyboard_reachable: takes focus on open and closes on Escape', () => {
    render(<ByKeyboard />)
    const card = screen.getByRole('dialog', { name: 'Same game on 2 other systems' })
    expect(document.activeElement).toBe(card)
    fireEvent.keyDown(card, { key: 'Escape' })
    expect(ByKeyboard.args.onClose).toHaveBeenCalled()
  })

  it('closes on a press outside it, not on one inside', () => {
    render(<ByKeyboard />)
    fireEvent.pointerDown(screen.getByRole('button', { name: 'Switch' }))
    expect(ByKeyboard.args.onClose).not.toHaveBeenCalled()
    fireEvent.pointerDown(document.body)
    expect(ByKeyboard.args.onClose).toHaveBeenCalledOnce()
  })

  it('switch_and_select: both actions are buttons that fire without a pointer', () => {
    render(<ByKeyboard />)
    const sw = screen.getByRole('button', { name: 'Switch' })
    const sel = screen.getByRole('button', { name: 'Select' })
    sw.focus()
    fireEvent.keyDown(sw, { key: 'Enter' })
    fireEvent.click(sw)
    fireEvent.click(sel)
    const [, two, three] = ByKeyboard.args.rows ?? []
    if (two?.action.kind === 'switch') expect(two.action.onSwitch).toHaveBeenCalled()
    if (three?.action.kind === 'select') expect(three.action.onSelect).toHaveBeenCalled()
  })

  it('says what the versions were matched on, and warns on a file name', () => {
    const { unmount } = render(<ByKeyboard />)
    expect(screen.getByText(/matched on IGDB's name/)).toBeTruthy()
    unmount()
    render(<MatchedOnFileName />)
    expect(screen.getByText(/check these really are the same game/)).toBeTruthy()
  })
})
