import { composeStories } from '@storybook/react'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { appStore } from '../../../store/store'
import * as stories from './SettingsView.stories'

const { FirstRun, InTheDesktop, OffLoopback } = composeStories(stories)

const region = (name: RegExp) => screen.getByRole('region', { name })
const toast = () => appStore.getState().ui.toasts.at(-1)?.text

async function page() {
  render(<FirstRun />)
  await screen.findByRole('list', { name: 'Setup' })
  await waitFor(() => expect(region(/^Library/).textContent).toContain('4 systems · 40 games'))
}

describe('SettingsView', () => {
  it('test_shell_reported: upgrades from browser to desktop mode when the engine says so', async () => {
    render(<InTheDesktop />)
    const diagnostics = await screen.findByRole('region', { name: /^Diagnostics/ })
    await waitFor(() => expect(diagnostics.textContent).toContain('Shelldesktop window'))
    const library = region(/^Library/)
    expect(within(library).getByRole('button', { name: 'Browse…' })).toBeTruthy()
    expect(within(library).getByRole('button', { name: 'Reveal' })).toBeTruthy()
    expect(
      within(region(/^Data and storage/)).getByRole('button', { name: 'Reveal the data folder' }),
    ).toBeTruthy()
  })

  it('offers no shell action where the engine says none answers', async () => {
    render(<OffLoopback />)
    await waitFor(() => expect(region(/^Library/).textContent).toContain('4 systems · 40 games'))
    expect(region(/^Diagnostics/).textContent).toContain('Shellbrowser')
    expect(screen.queryByRole('button', { name: 'Browse…' })).toBeNull()
    expect(screen.queryByRole('button', { name: /^Reveal/ })).toBeNull()
  })

  it('setup_steps: shows the steps in first-run order while one is left, and says which', async () => {
    await page()
    const steps = within(screen.getByRole('list', { name: 'Setup' })).getAllByRole('listitem')
    expect(steps.map((s) => s.textContent?.match(/(done|to do)/)?.[1])).toEqual([
      'done',
      'done',
      'to do',
    ])
    expect(region(/^Metadata and artwork/).textContent).toContain('no credentials')
  })

  it('test_fields: says the address, folders, last sync and recent errors (F15-S1)', async () => {
    await page()
    const diagnostics = region(/^Diagnostics/)
    await waitFor(() => expect(diagnostics.textContent).toContain('Addresshttp://127.0.0.1:8765/'))
    expect(diagnostics.textContent).toContain('Log folderX:/LocalAppData/ROM-Sync/data/logs')
    expect(diagnostics.textContent).toContain('Last syncno sync yet')
    expect(diagnostics.textContent).toContain('No job has failed.')
  })

  it('test_breakdown_matches_fixture: shows the data folder by part (F15-S2)', async () => {
    await page()
    const data = region(/^Data and storage/)
    const table = await within(data).findByRole('table', { name: /^Storage:/ })
    await waitFor(() => expect(within(table).getAllByRole('row')).toHaveLength(8))
    expect(within(table).getAllByRole('row').at(-1)?.textContent).toContain(
      'Embedded browser profile',
    )
  })

  it('states each detected transport in the transports section (F13-S8)', async () => {
    await page()
    const transports = region(/^Transports and tools/)
    const list = await within(transports).findByRole('list', { name: 'Detected transports' })
    expect(
      within(list)
        .getAllByRole('listitem')
        .map((li) => li.textContent),
    ).toEqual(['Drivesavailable1 drive(s)', 'MTPavailable0 storage(s)', 'ADBavailable2 device(s)'])
  })

  it('draws every section in first-run order from the registry, with its fields', async () => {
    await page()
    expect(
      screen
        .getAllByRole('heading', { level: 2 })
        .map((h) => h.textContent?.replace(/(edited|no .*|\d+ systems.*|credentials set)$/, '')),
    ).toEqual([
      'Setup',
      'Library',
      'Metadata and artwork',
      'Tag suggestions',
      'Transports and tools',
      'Sync behaviour and guards',
      'Data and storage',
      'Diagnostics',
    ])
    expect(
      within(region(/^Sync behaviour/)).getByRole('textbox', { name: 'Keep free on the device' }),
    ).toHaveProperty('value', '512.0 MB')
    expect(
      within(region(/^Diagnostics/)).getByRole('combobox', { name: 'Log level' }),
    ).toHaveProperty('value', 'info')
  })

  it('per_section_save: saves one section’s edits only, and leaves another section’s edit standing', async () => {
    await page()
    const transports = region(/^Transports and tools/)
    const sync = region(/^Sync behaviour/)
    fireEvent.change(within(transports).getByRole('textbox', { name: 'Device probe interval' }), {
      target: { value: '30' },
    })
    fireEvent.change(within(sync).getByRole('textbox', { name: 'Keep free on the device' }), {
      target: { value: '1 GB' },
    })
    expect(within(transports).getByText('edited')).toBeTruthy()
    fireEvent.click(within(transports).getByRole('button', { name: 'Save transports and tools' }))
    await waitFor(() => expect(toast()).toBe('Transports and tools saved'))
    expect(within(transports).queryByText('edited')).toBeNull()
    expect(within(sync).getByRole('textbox', { name: 'Keep free on the device' })).toHaveProperty(
      'value',
      '1 GB',
    )
    expect(within(sync).getByText('edited')).toBeTruthy()
  })

  it('refuses a value on its field and sends nothing', async () => {
    await page()
    const transports = region(/^Transports and tools/)
    fireEvent.change(within(transports).getByRole('textbox', { name: 'Device probe interval' }), {
      target: { value: '1' },
    })
    fireEvent.click(within(transports).getByRole('button', { name: 'Save transports and tools' }))
    expect(await within(transports).findByText('At least 5')).toBeTruthy()
    expect(toast()).toBeUndefined()
  })

  it('edit_survives_job: a rescan ending does not discard what is typed in another section', async () => {
    await page()
    const sync = region(/^Sync behaviour/)
    fireEvent.change(within(sync).getByRole('textbox', { name: 'Keep free on the device' }), {
      target: { value: '2 GB' },
    })
    fireEvent.click(within(region(/^Library/)).getByRole('button', { name: 'Rescan store' }))
    fireEvent.click(
      within(screen.getByRole('dialog', { name: 'Rescan the store' })).getByRole('button', {
        name: 'Rescan',
      }),
    )
    await waitFor(() => expect(toast()).toMatch(/^scan done/))
    expect(
      within(region(/^Sync behaviour/)).getByRole('textbox', { name: 'Keep free on the device' }),
    ).toHaveProperty('value', '2 GB')
  })

  it('takes the credentials without ever showing the secret, tests them, and completes setup', async () => {
    await page()
    const meta = region(/^Metadata and artwork/)
    fireEvent.change(within(meta).getByRole('textbox', { name: 'Twitch client ID' }), {
      target: { value: 'my-client' },
    })
    fireEvent.click(within(meta).getByRole('button', { name: 'Add credentials' }))
    fireEvent.change(within(meta).getByLabelText('New client secret'), {
      target: { value: 'a-secret-that-is-long-enough' },
    })
    fireEvent.click(within(meta).getByRole('button', { name: 'Test connection' }))
    await waitFor(() =>
      expect(within(meta).getByRole('status').textContent).toBe('connected: token, api ok'),
    )
    fireEvent.click(within(meta).getByRole('button', { name: 'Save metadata and artwork' }))
    await waitFor(() => expect(toast()).toBe('Metadata and artwork saved'))
    expect(await within(meta).findByText(/· 28 characters · not shown again/)).toBeTruthy()
    await waitFor(() => expect(screen.getByText(/^Setup complete\./)).toBeTruthy())
  })

  it('asks before upkeep that deletes, with what its dry run found', async () => {
    await page()
    const data = region(/^Data and storage/)
    const covers = await within(data).findByRole('button', { name: 'Delete unreferenced covers' })
    await waitFor(() => expect(covers.hasAttribute('disabled')).toBe(false))
    fireEvent.click(covers)
    const ask = screen.getByRole('dialog', { name: 'Delete unreferenced covers' })
    expect(ask.textContent).toContain('3 items, 585.9 KB')
    act(() => fireEvent.click(within(ask).getByRole('button', { name: 'Run' })))
    await waitFor(() => expect(toast()).toBe('Delete unreferenced covers: started'))
  })
})
