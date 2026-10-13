import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './LockedField.stories'

const { Locked, Empty, Opened, Refused } = composeStories(stories)

describe('LockedField', () => {
  it('locks a saved value until its edit icon is pressed', () => {
    render(<Locked />)
    const field = screen.getByRole('textbox', { name: 'Twitch client ID' }) as HTMLInputElement
    expect(field.readOnly).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Change Twitch client ID' }))
    expect(Locked.args.onUnlock).toHaveBeenCalledOnce()
  })

  it('leaves an empty field open, with no edit icon', () => {
    render(<Empty />)
    expect((screen.getByRole('textbox') as HTMLInputElement).readOnly).toBe(false)
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('puts the caret in the field it opens', () => {
    render(<Opened />)
    fireEvent.click(screen.getByRole('button', { name: 'Change Twitch client ID' }))
    const field = screen.getByRole('textbox', { name: 'Twitch client ID' })
    expect(document.activeElement).toBe(field)
    fireEvent.change(field, { target: { value: 'new' } })
    expect((field as HTMLInputElement).value).toBe('new')
    fireEvent.click(screen.getByRole('button', { name: 'Keep the saved Twitch client ID' }))
    expect((field as HTMLInputElement).value).toBe('abc123clientid')
    expect((field as HTMLInputElement).readOnly).toBe(true)
  })

  it('says a refusal with the field', () => {
    render(<Refused />)
    const field = screen.getByRole('textbox', { name: 'Twitch client ID' })
    expect(field.getAttribute('aria-invalid')).toBe('true')
    expect(field.getAttribute('aria-describedby')).toMatch(/error/)
    expect(screen.getByText('Must contain {system}')).toBeTruthy()
  })
})
