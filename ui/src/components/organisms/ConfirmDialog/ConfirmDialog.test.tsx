import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './ConfirmDialog.stories'

const { Danger } = composeStories(stories)

describe('ConfirmDialog', () => {
  it('asks in a named dialog with Cancel focused', () => {
    render(<Danger />)
    expect(screen.getByRole('dialog', { name: 'Clear the selection' })).toBeTruthy()
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Cancel' }))
  })

  it('confirms, or cancels by button or Escape', () => {
    render(<Danger />)
    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }))
    expect(Danger.args.onConfirm).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })
    expect(Danger.args.onCancel).toHaveBeenCalledTimes(2)
  })
})
