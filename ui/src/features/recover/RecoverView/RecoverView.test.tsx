import { composeStories } from '@storybook/react'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { appStore } from '../../../store/store'
import * as stories from './RecoverView.stories'

const { SomethingToRecover, NothingToRecover } = composeStories(stories)

const toasts = () => appStore.getState().ui.toasts.map((t) => t.text)

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

  it('rescan_after_place: recovers a file into the store, reads the store again, and it leaves the list', async () => {
    render(<SomethingToRecover />)
    await screen.findByRole('table', { name: 'On Thor, not in the store' })
    fireEvent.click(screen.getByRole('button', { name: 'Recover Hidden Gem (USA).sfc' }))
    await waitFor(() =>
      expect(toasts()).toContain(
        'Hidden Gem (USA).sfc placed in the store; reading the store again',
      ),
    )
    await waitFor(() => expect(toasts()).toContain('Hidden Gem (USA).sfc is in the library'))
    await waitFor(() => expect(screen.queryByText(/Hidden Gem/)).toBeNull())
  })

  it('place_refuses_existing_name: a name the store already has is reported, and nothing is replaced', async () => {
    render(<SomethingToRecover />)
    await screen.findByRole('table', { name: 'On Thor, not in the store' })
    fireEvent.click(screen.getByRole('button', { name: 'Recover Clash (USA).sfc' }))
    await waitFor(() =>
      expect(toasts()).toContain(
        'the store already has snes/Clash (USA).sfc; nothing was replaced',
      ),
    )
    expect(await screen.findByText('the store already has this name')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Recover Clash (USA).sfc' })).toBeNull()
  })

  it('offers no Recover for a folder', async () => {
    render(<SomethingToRecover />)
    await screen.findByRole('table', { name: 'On Thor, not in the store' })
    expect(screen.getByText('folders are not recovered')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Recover Translation Patch' })).toBeNull()
  })
})
