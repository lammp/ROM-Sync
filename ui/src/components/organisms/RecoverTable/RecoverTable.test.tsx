import { composeStories } from '@storybook/react'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './RecoverTable.stories'

const { Default, Nothing, Recoverable, Recovering } = composeStories(stories)

describe('RecoverTable', () => {
  it('states_removal_consequence: says what the next sync does to each item only the device holds', () => {
    render(<Default />)
    const rows = within(screen.getByRole('table', { name: 'On Thor, not in the store' }))
      .getAllByRole('row')
      .slice(1)
    expect(rows.map((r) => [...r.querySelectorAll('td')].map((c) => c.textContent))).toEqual([
      [
        'snes \\ Hidden Gem (USA).sfc',
        '2.00 MB',
        'not in the store, so the next sync removes it from the device',
        '',
      ],
      [
        'n64 \\ Translation Patch (folder)',
        '',
        'left alone: Nintendo 64 is not managed on this device',
        'folders are not recovered',
      ],
      ['nes \\ Homebrew.nes', '40.0 KB', 'left alone: nes is not a store system', ''],
    ])
  })

  it('says when the device holds nothing the store lacks', () => {
    render(<Nothing />)
    expect(screen.getByText('Everything on this device is in the store.')).toBeTruthy()
  })

  it('offers Recover for a file, never for a folder, and names a refused clash instead', () => {
    render(<Recoverable />)
    const cells = within(screen.getByRole('table'))
      .getAllByRole('row')
      .slice(1)
      .map((r) => r.querySelectorAll('td')[3]?.textContent)
    expect(cells).toEqual([
      'Recover',
      'the store already has this name',
      'folders are not recovered',
    ])
  })

  it('holds every Recover while one runs, and says which', () => {
    render(<Recovering />)
    expect(
      screen
        .getByRole('button', { name: 'Recovering Hidden Gem (USA).sfc' })
        .hasAttribute('disabled'),
    ).toBe(true)
  })
})
