import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PathField } from './PathField'
import * as stories from './PathField.stories'

const { Chosen, NoneChosen, Typed } = composeStories(stories)

describe('PathField', () => {
  it('is a button that opens the chooser, never a text field', () => {
    render(<Chosen />)
    expect(screen.queryByRole('textbox')).toBeNull()
    fireEvent.click(
      screen.getByRole('button', { name: 'Store root D:\\Games\\ROMs Choose folder…' }),
    )
    expect(Chosen.args.onChoose).toHaveBeenCalledOnce()
  })

  it('clears to nothing', () => {
    const onChange = vi.fn()
    render(
      <PathField
        label="Firmware folder"
        value="D:\\fw"
        kind="folder"
        onChoose={vi.fn()}
        onChange={onChange}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'clear firmware folder' }))
    expect(onChange).toHaveBeenCalledWith('')
  })

  it('says when nothing is chosen', () => {
    render(<NoneChosen />)
    expect(screen.getByText('No folder chosen')).toBeTruthy()
  })

  it('falls back to typing only where nothing can be chosen, and says why', () => {
    render(<Typed />)
    const input = screen.getByRole('textbox', { name: 'Store root' })
    expect(input.getAttribute('aria-describedby')).toBeTruthy()
    expect(screen.getByText(/can be chosen only on this computer/)).toBeTruthy()
  })
})
