import { composeStories } from '@storybook/react'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { appStore } from '../../../store/store'
import * as stories from './DevicesView.stories'

const push = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }))

const { EveryKind } = composeStories(stories)

beforeEach(() => {
  push.mockClear()
})

async function cards() {
  const list = await screen.findByRole('list', { name: 'Devices' })
  await waitFor(() => expect(within(list).getAllByRole('article')).toHaveLength(5))
  return list
}

describe('DevicesView', () => {
  it('lists the profiles first, then each device plugged in without one', async () => {
    render(<EveryKind />)
    const list = await cards()
    expect(
      within(list)
        .getAllByRole('article')
        .map((a) => a.getAttribute('aria-label')),
    ).toEqual([
      'Thor',
      'Deck card',
      'SD card (E:)',
      'Retroid (serial-2)',
      'Android device (serial-3)',
    ])
    expect(screen.getByText('unauthorized: accept the debugging prompt on the device')).toBeTruthy()
    expect(screen.getByText('carries ROM-Sync.json from another computer')).toBeTruthy()
    expect(screen.getByText('no profile yet')).toBeTruthy()
  })

  it('counts each profile’s selection and what its device holds', async () => {
    render(<EveryKind />)
    await cards()
    const thor = screen.getByRole('article', { name: 'Thor' })
    await waitFor(() => expect(thor.textContent).toMatch(/selected11/))
    expect(thor.textContent).toMatch(/on device1/)
    const deck = screen.getByRole('article', { name: 'Deck card' })
    await waitFor(() => expect(deck.textContent).toMatch(/selected10/))
    expect(deck.textContent).toContain('offline · last seen 2026-09-20 18:30')
  })

  it('sends Choose games to the library with the device chosen, and Contents to its page', async () => {
    render(<EveryKind />)
    await cards()
    const thor = screen.getByRole('article', { name: 'Thor' })
    fireEvent.click(within(thor).getByRole('button', { name: 'Choose games' }))
    expect(appStore.getState().selection.device).toBe('dev-1')
    expect(push).toHaveBeenLastCalledWith('/')
    fireEvent.click(within(thor).getByRole('button', { name: 'Contents' }))
    expect(push).toHaveBeenLastCalledWith('/devices?id=dev-1')
  })

  it('adopts another computer’s device and opens its page', async () => {
    render(<EveryKind />)
    await cards()
    fireEvent.click(screen.getByRole('button', { name: 'Adopt profile' }))
    await waitFor(() => expect(push).toHaveBeenCalledWith('/devices?id=dev-elsewhere'))
    expect(appStore.getState().ui.toasts.at(-1)?.text).toBe('Adopted Retroid')
  })

  it('makes a profile through the dialog and opens its page', async () => {
    render(<EveryKind />)
    await cards()
    fireEvent.click(screen.getByRole('button', { name: 'New profile…' }))
    const dialog = screen.getByRole('dialog', { name: 'New device profile' })
    expect(dialog.textContent).toContain('ROMs folder on the drive')
    fireEvent.change(within(dialog).getByRole('textbox', { name: 'Name' }), {
      target: { value: 'Card' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Create' }))
    await waitFor(() => expect(push).toHaveBeenCalledWith('/devices?id=dev-3'))
    expect(screen.queryByRole('dialog')).toBeNull()
  })
})
