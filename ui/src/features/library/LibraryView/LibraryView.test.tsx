import { composeStories } from '@storybook/react'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { appStore } from '../../../store/store'
import * as stories from './LibraryView.stories'

const push = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }))

const { Browsing, CuratingForThor, GameOpen } = composeStories(stories)

beforeEach(() => {
  push.mockClear()
})

describe('LibraryView', () => {
  it('lists the library and narrows it by a facet', async () => {
    render(<Browsing />)
    await screen.findByText(/^40 of 40/)
    fireEvent.click(screen.getByRole('button', { name: /^Super Nintendo ?\d+$/ }))
    await screen.findByText(/^10 of 40/)
    expect(appStore.getState().filters.chosen.system).toEqual(['snes'])
    expect(screen.queryByRole('group', { name: /^Selection for/ })).toBeNull()
  })

  it('summarises the device’s selection and sends a sync to the device’s page', async () => {
    appStore.getState().selection.choose('dev-1')
    render(<CuratingForThor />)
    const summary = await screen.findByRole('group', { name: 'Selection for Thor' })
    await waitFor(() => expect(summary.textContent).toContain('11 selected'))
    expect(summary.textContent).toContain('1 on device')
    fireEvent.click(await within(summary).findByRole('button', { name: /^Sync/ }))
    expect(push).toHaveBeenCalledWith('/devices?id=dev-1')
  })

  it('asks before a bulk change, and a cancel changes nothing', async () => {
    appStore.getState().selection.choose('dev-1')
    render(<CuratingForThor />)
    const summary = await screen.findByRole('group', { name: 'Selection for Thor' })
    await waitFor(() => expect(summary.textContent).toContain('11 selected'))
    fireEvent.click(within(summary).getByRole('button', { name: /^Select shown/ }))
    const dialog = screen.getByRole('dialog', { name: 'Select the games shown' })
    expect(dialog.textContent).toContain(
      'Select the 29 games shown that are not selected, for Thor.',
    )
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(summary.textContent).toContain('11 selected')
  })

  it('opens a game with its tags, leaving out the ones decided against', async () => {
    appStore.getState().library.open(1)
    render(<GameOpen />)
    const panel = await screen.findByRole('article', { name: 'Star Quest 1' })
    await waitFor(() => expect(panel.textContent).toContain('Space opera'))
    fireEvent.click(within(panel).getByRole('button', { name: 'Close details' }))
    expect(appStore.getState().library.current).toBeNull()
  })
})
