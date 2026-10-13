import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SettingControl.stories'

const { Text, Path, Size, Invalid, Flag, Choice } = composeStories(stories)

describe('SettingControl', () => {
  it('edits text, with what it takes said under it', () => {
    render(<Text />)
    const box = screen.getByRole('textbox', { name: 'Bind host' })
    fireEvent.change(box, { target: { value: '::1' } })
    expect(Text.args.onChange).toHaveBeenCalledWith('::1')
    expect(screen.getByText('Where the engine listens.')).toBeTruthy()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('chooses a path instead of typing it', () => {
    render(<Path />)
    expect(screen.queryByRole('textbox')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /^Store root/ }))
    expect(Path.args.onChoose).toHaveBeenCalledOnce()
    expect(screen.getByText('The store: the library every device is synced from.')).toBeTruthy()
  })

  it('takes a size as a size, its range in sizes, and offers the default', () => {
    render(<Size />)
    expect(screen.getByText('Headroom kept free after a sync. From 0 B to 8.00 GB.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'use the default (512.0 MB)' }))
    expect(Size.args.onDefault).toHaveBeenCalled()
  })

  it('shows a refusal on the field and says a restart is needed', () => {
    render(<Invalid />)
    expect(screen.getByRole('textbox').getAttribute('aria-invalid')).toBe('true')
    expect(screen.getByText('At most 65535')).toBeTruthy()
    expect(screen.getByText(/Takes effect after a restart\.$/)).toBeTruthy()
  })

  it('is a checkbox for a flag and a select for a choice', () => {
    render(<Flag />)
    fireEvent.click(screen.getByRole('checkbox', { name: 'Rescan on launch' }))
    expect(Flag.args.onChange).toHaveBeenCalledWith(false)
    render(<Choice />)
    fireEvent.change(screen.getByRole('combobox', { name: 'Log level' }), {
      target: { value: 'debug' },
    })
    expect(Choice.args.onChange).toHaveBeenCalledWith('debug')
  })
})
