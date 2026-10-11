import { composeStories } from '@storybook/react'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './RecoverTable.stories'

const { Default, Nothing } = composeStories(stories)

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
      ],
      [
        'n64 \\ Translation Patch (folder)',
        '',
        'left alone: Nintendo 64 is not managed on this device',
      ],
      ['nes \\ Homebrew.nes', '40.0 KB', 'left alone: nes is not a store system'],
    ])
  })

  it('says when the device holds nothing the store lacks', () => {
    render(<Nothing />)
    expect(screen.getByText('Everything on this device is in the store.')).toBeTruthy()
  })
})
