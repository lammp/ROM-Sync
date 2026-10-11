import { composeStories } from '@storybook/react'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './RecoverView.stories'

const { SomethingToRecover, NothingToRecover } = composeStories(stories)

describe('RecoverView', () => {
  it('lists_missing_from_store: lists, per device plugged in, what it holds that the store lacks', async () => {
    render(<SomethingToRecover />)
    const table = await screen.findByRole('table', { name: 'On Thor, not in the store' })
    const rows = within(table).getAllByRole('row').slice(1)
    expect(rows.map((r) => r.querySelector('td')?.textContent)).toEqual([
      'snes \\ Hidden Gem (USA).sfc',
      'snes \\ Clash (USA).sfc',
      'n64 \\ Translation Patch (folder)',
      'nes \\ Homebrew.nes',
    ])
  })

  it('states_removal_consequence: says the next sync removes what is in a managed system', async () => {
    render(<SomethingToRecover />)
    const table = await screen.findByRole('table', { name: 'On Thor, not in the store' })
    const fates = within(table)
      .getAllByRole('row')
      .slice(1)
      .map((r) => r.querySelectorAll('td')[2]?.textContent)
    expect(fates).toEqual([
      'not in the store, so the next sync removes it from the device',
      'not in the store, so the next sync removes it from the device',
      'left alone: Nintendo 64 is not managed on this device',
      'left alone: nes is not a store system',
    ])
  })

  it('says when a device holds nothing the store lacks', async () => {
    render(<NothingToRecover />)
    expect(await screen.findByText('Everything on this device is in the store.')).toBeTruthy()
  })
})
