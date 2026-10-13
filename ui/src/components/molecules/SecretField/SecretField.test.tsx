import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { savedOn } from './SecretField'
import * as stories from './SecretField.stories'

const { Empty, Saved, Replacing, Removing, Round } = composeStories(stories)
const field = () => screen.getByLabelText('Client secret') as HTMLInputElement

describe('SecretField', () => {
  it('is open when nothing is saved, and says why it matters', () => {
    render(<Empty />)
    expect(field().readOnly).toBe(false)
    fireEvent.change(field(), { target: { value: 'abc' } })
    expect(Empty.args.onDraft).toHaveBeenCalledWith({ kind: 'typed', text: 'abc' })
    expect(screen.getByText(/libretro box art does not/)).toBeTruthy()
  })

  it('locks a saved secret as dots, never its value, with edit and remove', () => {
    render(<Saved />)
    expect(field().readOnly).toBe(true)
    expect(field().value).toMatch(/^•+$/)
    expect(screen.getByText(/Saved 8 Oct 2026 · 30 characters/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Show/ })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Remove the saved client secret' }))
    expect(Saved.args.onDraft).toHaveBeenCalledWith({ kind: 'remove' })
  })

  it('shows what is typed only when the eye is pressed, and warns of a short one', () => {
    render(<Replacing />)
    expect(field().type).toBe('password')
    const eye = screen.getByRole('button', { name: 'Show the client secret' })
    expect(eye.getAttribute('aria-pressed')).toBe('false')
    fireEvent.click(eye)
    expect(field().type).toBe('text')
    expect(screen.getByRole('button', { name: 'Hide the client secret' })).toBeTruthy()
    expect(screen.getByText(/shorter than a Twitch secret/)).toBeTruthy()
  })

  it('says a removal waits for the save, and can be undone', () => {
    render(<Removing />)
    expect(screen.getByText('Removed when you save.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Keep the saved client secret' }))
    expect(Removing.args.onDraft).toHaveBeenCalledWith({ kind: 'keep' })
  })

  it('opens with the caret in it, and locks again when the saved one is kept', () => {
    render(<Round />)
    fireEvent.click(screen.getByRole('button', { name: 'Enter a new client secret' }))
    expect(document.activeElement).toBe(field())
    fireEvent.click(screen.getByRole('button', { name: 'Keep the saved client secret' }))
    expect(field().readOnly).toBe(true)
  })

  it('writes a saved date as a day, keeping a date it cannot read', () => {
    expect(savedOn('2026-10-08T09:00:00Z')).toBe('8 Oct 2026')
    expect(savedOn('not a date at all')).toBe('not a date')
    expect(savedOn(null)).toBe('')
  })
})
