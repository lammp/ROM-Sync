import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './NewProfileDialog.stories'

const { Empty, Busy, Refused } = composeStories(stories)

describe('NewProfileDialog', () => {
  it('says what Create will do, and needs a name first', () => {
    render(<Empty />)
    const create = screen.getByRole('button', { name: 'Create' })
    expect(create.hasAttribute('disabled')).toBe(true)
    expect(screen.getByText('Name the profile to create it.')).toBeTruthy()
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: ' Card ' } })
    expect(
      screen.getByText(
        'Creates the profile “Card” with its ROMs at ROMs on this drive. ROM-Sync.json will be written there.',
      ),
    ).toBeTruthy()
    fireEvent.click(create)
    expect(Empty.args.onCreate).toHaveBeenCalledWith('Card', true)
  })

  it('leaves the marker unwritten when asked, and cancels without creating', () => {
    render(<Empty />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: 'Card' } })
    fireEvent.click(screen.getByRole('checkbox'))
    expect(screen.queryByText(/ROM-Sync.json will be written/)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(Empty.args.onCancel).toHaveBeenCalled()
    expect(Empty.args.onCreate).not.toHaveBeenCalled()
  })

  it('cannot be sent twice while it is creating', () => {
    render(<Busy />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: 'Card' } })
    expect(screen.getByRole('button', { name: 'Creating…' }).hasAttribute('disabled')).toBe(true)
  })

  it('shows the engine’s refusal on the name', () => {
    render(<Refused />)
    expect(screen.getByText('that device is not attached')).toBeTruthy()
  })
})
