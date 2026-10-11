import { composeStories } from '@storybook/react'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fakeFetch, freshWorld } from '../../../../e2e/fake/world'
import { PROBE_MS } from '../../../queries/devices/devices'
import { EngineProvider, createEngine } from '../../../queries/engine/engine'
import { DeviceView } from './DeviceView'
import { appStore } from '../../../store/store'
import * as stories from './DeviceView.stories'

const push = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }))

const { Connected, NotPluggedIn, Unknown } = composeStories(stories)

beforeEach(() => {
  push.mockClear()
})

async function page() {
  render(<Connected />)
  await screen.findByRole('heading', { name: /^Thor/ })
  await waitFor(() => expect(screen.getByText(/Sync will/)).toBeTruthy())
}

describe('DeviceView', () => {
  it('shows the device, its systems, what a sync would do and its history', async () => {
    await page()
    expect(screen.getByText('connected')).toBeTruthy()
    expect(
      screen.getByText(/ADB · ROMs folder: \/storage\/emulated\/0\/ROMs · .* free of/),
    ).toBeTruthy()
    const rows = within(screen.getByRole('table', { name: 'Systems' })).getAllByRole('row')
    expect(rows).toHaveLength(5)
    expect(screen.getByRole('radiogroup', { name: 'Selection for Super Nintendo' })).toBeTruthy()
    expect(screen.getByText(/send 10/)).toBeTruthy()
    expect(screen.getByText('no runs yet')).toBeTruthy()
    expect(
      await screen.findByText('Not read yet: open System files and press Refresh from device.'),
    ).toBeTruthy()
  })

  it('changes a system’s mode through the engine', async () => {
    await page()
    const n64 = screen.getByRole('radiogroup', { name: 'Selection for Nintendo 64' })
    fireEvent.click(within(n64).getByRole('radio', { name: 'all' }))
    await waitFor(() =>
      expect(within(n64).getByRole('radio', { name: 'all' }).getAttribute('aria-checked')).toBe(
        'true',
      ),
    )
  })

  it('asks before a sync and begins tracking it when the engine starts one', async () => {
    await page()
    fireEvent.click(screen.getByRole('button', { name: 'Sync' }))
    const dialog = screen.getByRole('dialog', { name: 'Sync Thor' })
    expect(within(dialog).getByRole('table').textContent).toContain('Send10')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Start' }))
    await waitFor(() => expect(appStore.getState().sync.running?.device).toBe('dev-1'))
    expect(appStore.getState().sync.running?.start).toMatchObject({ removesTotal: 0, onDevice: 1 })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(screen.getByRole('button', { name: 'Scan device' }).hasAttribute('disabled')).toBe(true)
  })

  it('scans the device as a job and says what it read', async () => {
    await page()
    fireEvent.click(screen.getByRole('button', { name: 'Scan device' }))
    await waitFor(() =>
      expect(appStore.getState().ui.toasts.at(-1)?.text).toBe('Read 1 game from the device'),
    )
  })

  it('renames the profile, and writes the marker only once asked', async () => {
    await page()
    fireEvent.click(screen.getByRole('button', { name: 'Rename' }))
    const rename = screen.getByRole('dialog', { name: 'Rename device' })
    fireEvent.change(within(rename).getByRole('textbox'), { target: { value: 'AYN Thor' } })
    fireEvent.click(within(rename).getByRole('button', { name: 'Rename' }))
    await screen.findByRole('heading', { name: /^AYN Thor/ })
    fireEvent.click(screen.getByRole('button', { name: 'Write ROM-Sync.json' }))
    const ask = screen.getByRole('dialog', { name: 'Write ROM-Sync.json' })
    fireEvent.click(within(ask).getByRole('button', { name: 'Write' }))
    await waitFor(() =>
      expect(appStore.getState().ui.toasts.at(-1)?.text).toBe('ROM-Sync.json written'),
    )
  })

  it('sends Select games in Library to the library with the device chosen', async () => {
    await page()
    fireEvent.click(screen.getByRole('button', { name: 'Select games in Library' }))
    expect(appStore.getState().selection.device).toBe('dev-1')
    expect(push).toHaveBeenCalledWith('/')
  })

  it('keeps an unplugged device’s figures and offers no sync', async () => {
    render(<NotPluggedIn />)
    await screen.findByText('not plugged in')
    expect(screen.getByText(/last seen 2026-09-20 18:30/)).toBeTruthy()
    expect(screen.getByText('Plug the device in to see what a sync would do.')).toBeTruthy()
  })

  it('says when there is no such device', async () => {
    render(<Unknown />)
    await screen.findByRole('heading', { name: 'Device not found' })
    fireEvent.click(screen.getByRole('button', { name: 'All devices' }))
    expect(push).toHaveBeenCalledWith('/devices')
  })

  it('watcher_is_a_query: asks at the probe interval, says a pull-out, and stops when the page goes', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const world = freshWorld()
      const fetch = fakeFetch(world)
      let probes = 0
      const engine = createEngine({
        fetch: ((r: Request) => {
          if (new URL(r.url).pathname === '/api/v1/devices') probes++
          return fetch(r)
        }) as typeof globalThis.fetch,
        baseUrl: 'http://engine.test',
        retry: 0,
      })
      const { unmount } = render(
        <EngineProvider engine={engine}>
          <DeviceView id="dev-1" />
        </EngineProvider>,
      )
      await screen.findByText('connected')
      expect(probes).toBe(1)
      world.attached = world.attached.filter((a) => a.ref !== world.profiles[0]?.ref)
      await act(() => vi.advanceTimersByTimeAsync(PROBE_MS))
      await screen.findByText('not plugged in')
      expect(probes).toBe(2)
      expect(appStore.getState().ui.toasts.at(-1)?.text).toBe('Thor disconnected')
      unmount()
      await act(() => vi.advanceTimersByTimeAsync(PROBE_MS * 3))
      expect(probes).toBe(2)
    } finally {
      vi.useRealTimers()
    }
  })
})
