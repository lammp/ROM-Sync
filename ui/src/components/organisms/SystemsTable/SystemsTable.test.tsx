import { composeStories } from '@storybook/react'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { overrideWord } from './SystemsTable'
import * as stories from './SystemsTable.stories'

const { Default, Busy, Empty } = composeStories(stories)

describe('SystemsTable', () => {
  it('shows each system’s store and device figures and its mode, and changes the mode', () => {
    render(<Default />)
    const table = screen.getByRole('table', { name: 'Systems' })
    const rows = within(table).getAllByRole('row').slice(1)
    expect(rows.map((r) => r.querySelector('td')?.textContent)).toEqual([
      'Super Nintendo snes',
      'Game Boy Advance gba',
      'Nintendo 64 n64',
      'saves on device, not a store system: left alone',
    ])
    expect(rows[0]?.textContent).toContain('12 excluded')
    expect(rows[1]?.textContent).toContain('4 picked')
    const n64 = screen.getByRole('radiogroup', { name: 'Selection for Nintendo 64' })
    expect(
      within(n64).getByRole('radio', { name: 'left alone' }).getAttribute('aria-checked'),
    ).toBe('true')
    fireEvent.click(within(n64).getByRole('radio', { name: 'none' }))
    expect(Default.args.onMode).toHaveBeenCalledWith('n64', 'none')
    expect(screen.queryByRole('radiogroup', { name: 'Selection for saves' })).toBeNull()
  })

  it('holds the modes while the device is busy', () => {
    render(<Busy />)
    expect(screen.getAllByRole('radio').every((r) => r.hasAttribute('disabled'))).toBe(true)
  })

  it('says when the store has no systems', () => {
    render(<Empty />)
    expect(screen.getByText('No systems in the store yet.')).toBeTruthy()
  })

  it('words an override by the mode it goes against', () => {
    const row = { key: 'x', label: 'X', store: null, device: { n: 0, bytes: 0 }, overrides: 0 }
    expect(overrideWord({ ...row, mode: 'all' })).toBe('')
    expect(overrideWord({ ...row, mode: 'all', overrides: 1 })).toBe('1 excluded')
    expect(overrideWord({ ...row, mode: 'none', overrides: 2 })).toBe('2 picked')
  })
})
