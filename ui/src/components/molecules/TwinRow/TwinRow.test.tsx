import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './TwinRow.stories'

const { ThisOne, Switch, SelectAsWell, Kept } = composeStories(stories)

describe('TwinRow', () => {
  it('names the card own row and offers nothing on it', () => {
    render(<ThisOne />)
    expect(screen.getByText('this one')).toBeTruthy()
    expect(screen.getByText('selected · on device')).toBeTruthy()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('switches, opens and says when a match is loose', () => {
    render(<Switch />)
    fireEvent.click(screen.getByRole('button', { name: 'Switch' }))
    fireEvent.click(screen.getByRole('button', { name: /Majora/ }))
    const action = Switch.args.action
    if (action?.kind === 'switch') expect(action.onSwitch).toHaveBeenCalled()
    expect(Switch.args.onOpen).toHaveBeenCalled()
    expect(screen.getByText('loose match')).toBeTruthy()
  })

  it('selects as well, or says the version is kept', () => {
    const { unmount } = render(<SelectAsWell />)
    fireEvent.click(screen.getByRole('button', { name: 'Select' }))
    const action = SelectAsWell.args.action
    if (action?.kind === 'select') expect(action.onSelect).toHaveBeenCalled()
    unmount()
    render(<Kept />)
    expect(screen.getByText('kept')).toBeTruthy()
  })
})
