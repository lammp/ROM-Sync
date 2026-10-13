import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SettingsSection.stories'

const { Clean, Edited, Saving, Problem, NothingToSave, WithActions, WithGraphic } =
  composeStories(stories)

describe('SettingsSection', () => {
  it('is a region named by its title, saving only once something is edited', () => {
    render(<Clean />)
    expect(screen.getByRole('region', { name: /^Library/ }).id).toBe('library')
    expect(screen.getByRole('button', { name: 'Save library' }).hasAttribute('disabled')).toBe(true)
    expect(screen.getByText('4 systems')).toBeTruthy()
  })

  it('says it is edited and saves', () => {
    render(<Edited />)
    expect(screen.getByText('edited')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Save library' }))
    expect(Edited.args.onSave).toHaveBeenCalledTimes(1)
  })

  it('cannot be saved twice at once', () => {
    render(<Saving />)
    expect(screen.getByRole('button', { name: 'Saving…' }).hasAttribute('disabled')).toBe(true)
  })

  it('says a problem in words', () => {
    render(<Problem />)
    expect(screen.getByText('no store chosen')).toBeTruthy()
  })

  it('has no Save when there is nothing to save', () => {
    render(<NothingToSave />)
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('puts its main actions at its top, before its settings', () => {
    render(<WithActions />)
    const actions = screen.getByRole('group', { name: 'Library: actions' })
    const text = screen.getByText('Store root and rescan.')
    expect(actions.compareDocumentPosition(text) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Rescan ROMs folder' })).toBeTruthy()
  })

  it('carries a graphic after its actions and before its settings, and takes the width it is given', () => {
    render(<WithGraphic />)
    const region = screen.getByRole('region', { name: /^Library/ })
    expect(region.className).toMatch(/wide/)
    const graphic = screen.getByText('The tracker')
    const actions = screen.getByRole('group', { name: 'Library: actions' })
    expect(actions.compareDocumentPosition(graphic) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(
      graphic.compareDocumentPosition(screen.getByText('Store root and rescan.')) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })
})
