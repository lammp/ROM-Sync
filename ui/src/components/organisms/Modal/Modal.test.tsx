import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { Modal } from './Modal'
import * as stories from './Modal.stories'

const { Open } = composeStories(stories)

function Opener() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Open
      </button>
      {open && (
        <Modal title="Confirm" onClose={() => setOpen(false)}>
          <button type="button">Yes</button>
        </Modal>
      )}
    </>
  )
}

describe('Modal', () => {
  it('role_and_name: a modal dialog named by its title', () => {
    render(<Open />)
    const dialog = screen.getByRole('dialog', { name: 'Remove profile' })
    expect(dialog.getAttribute('aria-modal')).toBe('true')
  })

  it('moves focus in on open', () => {
    render(<Open />)
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Cancel' }))
  })

  it('trap: Tab and Shift+Tab stay inside', () => {
    render(<Open />)
    const cancel = screen.getByRole('button', { name: 'Cancel' })
    // the close button is the last control, after the content
    const close = screen.getByRole('button', { name: 'Close' })
    close.focus()
    fireEvent.keyDown(close, { key: 'Tab' })
    expect(document.activeElement).toBe(cancel)
    fireEvent.keyDown(cancel, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(close)
  })

  it('escape: closes', () => {
    render(<Open />)
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })
    expect(Open.args.onClose).toHaveBeenCalled()
  })

  it('restore: gives focus back to what opened it', () => {
    render(<Opener />)
    const opener = screen.getByRole('button', { name: 'Open' })
    opener.focus()
    fireEvent.click(opener)
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Yes' }))
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(opener)
  })

  it('closes on a click on the page around it, not on one inside', () => {
    const onClose = vi.fn()
    render(
      <Modal title="T" onClose={onClose}>
        <p>inside</p>
      </Modal>,
    )
    fireEvent.mouseDown(screen.getByText('inside'))
    fireEvent.mouseDown(screen.getByRole('dialog'))
    expect(onClose).not.toHaveBeenCalled()
    const around = screen.getByRole('dialog').parentElement
    if (!around) throw new Error('no backdrop')
    fireEvent.mouseDown(around)
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('always has a close button, after the content', () => {
    const onClose = vi.fn()
    render(
      <Modal title="Choose a folder" onClose={onClose}>
        <button type="button">Choose</button>
      </Modal>,
    )
    const close = screen.getByRole('button', { name: 'Close' })
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Choose' }))
    fireEvent.click(close)
    expect(onClose).toHaveBeenCalledOnce()
  })
})
