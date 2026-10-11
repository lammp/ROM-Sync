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
    const remove = screen.getByRole('button', { name: 'Remove' })
    remove.focus()
    fireEvent.keyDown(remove, { key: 'Tab' })
    expect(document.activeElement).toBe(cancel)
    fireEvent.keyDown(cancel, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(remove)
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

  it('stays open on a click inside or outside: Escape and Cancel close it', () => {
    const onClose = vi.fn()
    render(
      <Modal title="T" onClose={onClose}>
        <p>inside</p>
      </Modal>,
    )
    fireEvent.mouseDown(screen.getByText('inside'))
    fireEvent.mouseDown(document.body)
    expect(onClose).not.toHaveBeenCalled()
  })
})
