import { composeStories } from '@storybook/react'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { appStore } from '../../../store/store'
import * as stories from './SystemFilesView.stories'

const { StoreOnly, ForThor } = composeStories(stories)

const toast = () => appStore.getState().ui.toasts.at(-1)?.text

async function thor() {
  appStore.getState().selection.choose('dev-1')
  render(<ForThor />)
  await screen.findByRole('heading', { name: 'Thor: system files' })
}

async function surveyed() {
  await thor()
  fireEvent.click(screen.getByRole('button', { name: 'Refresh from device' }))
  await waitFor(() => expect(toast()).toBe('Read 12 entries from the device'))
  await screen.findByText(/^device read 2026-10-11 12:00/)
}

describe('SystemFilesView', () => {
  it('shows the store’s copies, and the store folder, with no device chosen', async () => {
    render(<StoreOnly />)
    const table = await screen.findByRole('table', { name: 'System files in the store' })
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(
      screen.getByText('Pick a device in the header to see what its emulators have and need.', {
        exact: false,
      }),
    ).toBeTruthy()
    expect(await screen.findByText('D:\\Games\\ROMs\\bios')).toBeTruthy()
  })

  it('asks for a device that is chosen but not plugged in, and still shows the store', async () => {
    appStore.getState().selection.choose('dev-2')
    render(<StoreOnly />)
    expect(
      await screen.findByText(/Plug Deck card in to see what its emulators have and need/),
    ).toBeTruthy()
    expect(await screen.findByRole('table', { name: 'System files in the store' })).toBeTruthy()
  })

  it('lists the device’s systems, picks one with games first, and says the device is not read yet', async () => {
    await thor()
    expect(screen.getByText('device not read yet')).toBeTruthy()
    const list = await screen.findByRole('navigation', { name: 'Systems' })
    expect(
      within(list)
        .getAllByRole('button')
        .map((b) => b.textContent?.split(/(?=not scanned|nothing needed|ready|missing)/)[0]),
    ).toEqual([
      'Super Nintendo',
      'Game Boy Advance',
      'Nintendo 64',
      'PlayStation 2',
      'Other filesnone',
    ])
    expect(screen.getByRole('article', { name: /^Super Nintendo/ })).toBeTruthy()
  })

  it('reads the device, stages a system’s files, and removes them again', async () => {
    await surveyed()
    fireEvent.click(screen.getByRole('button', { name: /^Game Boy Advance/ }))
    const detail = screen.getByRole('article', { name: /^Game Boy Advance/ })
    expect(detail.textContent).toContain('Missing: gba_bios.bin')
    fireEvent.click(within(detail).getByRole('button', { name: 'Add' }))
    await waitFor(() => expect(toast()).toBe('Placed 1 file'))
    await waitFor(() =>
      expect(within(detail).getByRole('button', { name: 'Remove' }).hasAttribute('disabled')).toBe(
        false,
      ),
    )
    fireEvent.click(within(detail).getByRole('button', { name: 'Remove' }))
    await waitFor(() => expect(toast()).toBe('Removed 1 item'))
  })

  it('asks before a stray file is removed from the device', async () => {
    await surveyed()
    fireEvent.click(screen.getByRole('button', { name: /^Other files/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'Remove old_bios.bin' }))
    const ask = screen.getByRole('dialog', { name: 'Remove old_bios.bin' })
    expect(ask.textContent).toContain('ROM-Sync/bios/gba/old_bios.bin')
    fireEvent.click(within(ask).getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('button', { name: 'Remove old_bios.bin' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Remove old_bios.bin' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Remove' }))
    await screen.findByText('nothing stray')
  })

  it('waits for a running sync before touching the device', async () => {
    await thor()
    act(() => {
      appStore
        .getState()
        .sync.begin('job-x', 'dev-1', { bytesTotal: 1, removesTotal: 0, onDevice: 0, free: null })
    })
    fireEvent.click(screen.getByRole('button', { name: 'Refresh from device' }))
    expect(toast()).toBe('Wait for the sync to finish')
  })
})
