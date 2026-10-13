import { composeStories } from '@storybook/react'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { appStore } from '../../../store/store'
import * as stories from './SettingsView.stories'

const { FirstRun, InTheDesktop, OffLoopback, MetadataActions, PassAlreadyRunning } =
  composeStories(stories)

const region = (name: RegExp) => screen.getByRole('region', { name })
const toast = () => appStore.getState().ui.toasts.at(-1)?.text

/** Opens a settings tab and gives its section. */
function tab(name: RegExp): HTMLElement {
  fireEvent.click(screen.getByRole('tab', { name }))
  return region(name)
}

async function page() {
  render(<FirstRun />)
  await screen.findByRole('tablist', { name: 'Settings groups' })
  await waitFor(() => expect(region(/^Library/).textContent).toContain('4 systems · 40 games'))
}

describe('SettingsView', () => {
  // the open tab is kept in the address; each test starts on the first
  beforeEach(() => window.history.replaceState(null, '', window.location.pathname))

  it('test_shell_reported: upgrades from browser to desktop mode when the engine says so', async () => {
    render(<InTheDesktop />)
    await screen.findByRole('tablist', { name: 'Settings groups' })
    const diagnostics = tab(/^Diagnostics/)
    await waitFor(() => expect(diagnostics.textContent).toContain('Shelldesktop window'))
    const library = tab(/^Library/)
    expect(within(library).getByRole('button', { name: /^ROMs folder/ })).toBeTruthy()
    expect(within(library).queryByRole('textbox', { name: 'ROMs folder' })).toBeNull()
    expect(within(library).getByRole('button', { name: 'Reveal' })).toBeTruthy()
    expect(
      within(tab(/^Data and storage/)).getByRole('button', { name: 'Reveal the data folder' }),
    ).toBeTruthy()
  })

  it('offers no shell action where the engine says none answers', async () => {
    render(<OffLoopback />)
    await waitFor(() => expect(region(/^Library/).textContent).toContain('4 systems · 40 games'))
    // nothing here may read this computer's folders, so the path is typed
    expect(within(region(/^Library/)).getByRole('textbox', { name: 'ROMs folder' })).toBeTruthy()
    expect(tab(/^Diagnostics/).textContent).toContain('Shellbrowser')
    expect(screen.queryByRole('button', { name: /^Reveal/ })).toBeNull()
  })

  it('tabs: one per group in first-run order, the first shown, the setup steps gone to notifications', async () => {
    await page()
    expect(screen.getAllByRole('tab').map((t) => t.textContent)).toEqual([
      'Library',
      'Metadata and artwork',
      'Tag suggestions',
      'Transports and tools',
      'Sync behaviour and guards',
      'Data and storage',
      'Diagnostics',
    ])
    expect(screen.getByRole('tab', { name: 'Library' }).getAttribute('aria-selected')).toBe('true')
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1)
    expect(screen.queryByRole('list', { name: 'Setup' })).toBeNull()
    expect(tab(/^Metadata and artwork/).textContent).toContain('no credentials')
  })

  it('test_fields: says the address, folders, last sync and recent errors (F15-S1)', async () => {
    await page()
    const diagnostics = tab(/^Diagnostics/)
    await waitFor(() => expect(diagnostics.textContent).toContain('Addresshttp://127.0.0.1:8765/'))
    expect(diagnostics.textContent).toContain('Log folderX:/LocalAppData/ROM-Sync/data/logs')
    expect(diagnostics.textContent).toContain('Last syncno sync yet')
    expect(diagnostics.textContent).toContain('No job has failed.')
  })

  it('test_breakdown_matches_fixture: shows the data folder by part (F15-S2)', async () => {
    await page()
    const data = tab(/^Data and storage/)
    const table = await within(data).findByRole('table', { name: /^Storage:/ })
    await waitFor(() => expect(within(table).getAllByRole('row')).toHaveLength(8))
    expect(within(table).getAllByRole('row').at(-1)?.textContent).toContain(
      'Embedded browser profile',
    )
  })

  it('states each detected transport in the transports section (F13-S8)', async () => {
    await page()
    const transports = tab(/^Transports and tools/)
    const list = await within(transports).findByRole('list', { name: 'Detected transports' })
    expect(
      within(list)
        .getAllByRole('listitem')
        .map((li) => li.textContent),
    ).toEqual(['Drivesavailable1 drive(s)', 'MTPavailable0 storage(s)', 'ADBavailable2 device(s)'])
  })

  it("draws each tab's section from the registry, with its fields", async () => {
    await page()
    expect(
      within(tab(/^Sync behaviour/)).getByRole('combobox', { name: 'Keep free on the device' }),
    ).toHaveProperty('value', '512.0 MB')
    expect(within(tab(/^Diagnostics/)).getByRole('combobox', { name: 'Log level' })).toHaveProperty(
      'value',
      'info',
    )
  })

  it('per_section_save: Save saves the tab it is in, and an edit in another tab stands, marked', async () => {
    await page()
    fireEvent.change(
      within(tab(/^Transports and tools/)).getByRole('textbox', { name: 'Device probe interval' }),
      { target: { value: '30' } },
    )
    fireEvent.change(
      within(tab(/^Sync behaviour/)).getByRole('combobox', { name: 'Keep free on the device' }),
      { target: { value: '1.00 GB' } },
    )
    await waitFor(() =>
      expect(
        screen.getByRole('tab', { name: 'Sync behaviour and guards, unsaved changes' }),
      ).toBeTruthy(),
    )
    expect(screen.getByRole('tab', { name: 'Transports and tools, unsaved changes' })).toBeTruthy()
    const transports = tab(/^Transports and tools/)
    expect(within(transports).getByText('edited')).toBeTruthy()
    fireEvent.click(within(transports).getByRole('button', { name: 'Save transports and tools' }))
    await waitFor(() => expect(toast()).toBe('Transports and tools saved'))
    expect(within(transports).queryByText('edited')).toBeNull()
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: 'Transports and tools' })).toBeTruthy(),
    )
    const sync = tab(/^Sync behaviour/)
    expect(within(sync).getByRole('combobox', { name: 'Keep free on the device' })).toHaveProperty(
      'value',
      '1.00 GB',
    )
    expect(within(sync).getByText('edited')).toBeTruthy()
  })

  it("Cancel drops the tab's edits and its mark", async () => {
    await page()
    const sync = tab(/^Sync behaviour/)
    fireEvent.change(within(sync).getByRole('combobox', { name: 'Keep free on the device' }), {
      target: { value: '1.00 GB' },
    })
    fireEvent.click(within(sync).getByRole('button', { name: 'Cancel' }))
    expect(within(sync).getByRole('combobox', { name: 'Keep free on the device' })).toHaveProperty(
      'value',
      '512.0 MB',
    )
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: 'Sync behaviour and guards' })).toBeTruthy(),
    )
  })

  it('refuses a value on its field and sends nothing', async () => {
    await page()
    const transports = tab(/^Transports and tools/)
    fireEvent.change(within(transports).getByRole('textbox', { name: 'Device probe interval' }), {
      target: { value: '1' },
    })
    fireEvent.click(within(transports).getByRole('button', { name: 'Save transports and tools' }))
    expect(await within(transports).findByText('At least 5')).toBeTruthy()
    expect(toast()).toBeUndefined()
  })

  it('edit_survives_job: a rescan ending does not discard what is typed in another section', async () => {
    await page()
    const sync = tab(/^Sync behaviour/)
    fireEvent.change(within(sync).getByRole('combobox', { name: 'Keep free on the device' }), {
      target: { value: '2.00 GB' },
    })
    fireEvent.click(within(tab(/^Library/)).getByRole('button', { name: 'Rescan ROMs folder' }))
    fireEvent.click(
      within(screen.getByRole('dialog', { name: 'Rescan the ROMs folder' })).getByRole('button', {
        name: 'Rescan',
      }),
    )
    await waitFor(() => expect(toast()).toMatch(/^scan done/))
    expect(
      within(tab(/^Sync behaviour/)).getByRole('combobox', { name: 'Keep free on the device' }),
    ).toHaveProperty('value', '2.00 GB')
  })

  it('takes the credentials without ever showing the secret, tests them, then locks both', async () => {
    await page()
    const meta = tab(/^Metadata and artwork/)
    fireEvent.change(within(meta).getByRole('textbox', { name: 'Twitch client ID' }), {
      target: { value: 'my-client' },
    })
    fireEvent.change(within(meta).getByLabelText('Client secret'), {
      target: { value: 'a-secret-that-is-long-enough' },
    })
    const test = within(meta).getByRole('button', { name: 'Test connection' })
    fireEvent.click(test)
    await waitFor(() =>
      expect(within(meta).getByRole('status').textContent).toBe('connected: token, api ok'),
    )
    expect(test.querySelector('svg')?.getAttribute('data-icon')).toBe('tick')
    fireEvent.click(within(meta).getByRole('button', { name: 'Save metadata and artwork' }))
    await waitFor(() => expect(toast()).toBe('Metadata and artwork saved'))
    expect(
      await within(meta).findByText(/· 28 characters\. A saved secret is never shown/),
    ).toBeTruthy()
    await waitFor(() => expect(meta.textContent).toContain('credentials set'))
    const id = within(meta).getByRole('textbox', { name: 'Twitch client ID' }) as HTMLInputElement
    expect(id.readOnly).toBe(true)
    expect((within(meta).getByLabelText('Client secret') as HTMLInputElement).readOnly).toBe(true)
    fireEvent.click(within(meta).getByRole('button', { name: 'Change Twitch client ID' }))
    expect(id.readOnly).toBe(false)
  })

  it('runs the metadata from the top of its tab: Run Initial, then Update, and a Refresh that asks', async () => {
    render(<MetadataActions />)
    fireEvent.click(await screen.findByRole('tab', { name: 'Metadata and artwork' }))
    const actions = screen.getByRole('group', { name: 'Metadata and artwork: actions' })
    const initial = await within(actions).findByRole('button', { name: 'Run Initial' })
    await waitFor(() => expect(initial.hasAttribute('disabled')).toBe(false))
    expect(
      within(actions).getByRole('button', { name: 'Refresh Metadata' }).getAttribute('title'),
    ).toBe('Run the initial pass first')
    fireEvent.click(initial)
    const update = await within(actions).findByRole('button', { name: 'Update Metadata' })
    await waitFor(() => expect(update.querySelector('svg')?.getAttribute('data-icon')).toBe('tick'))
    const tracker = screen.getByRole('region', { name: 'Metadata progress' })
    expect(within(tracker).getByText('Not looked up').nextElementSibling?.textContent).toBe('0')
    fireEvent.click(within(actions).getByRole('button', { name: 'Refresh Metadata' }))
    const ask = screen.getByRole('dialog', { name: 'Refresh metadata' })
    expect(ask.textContent).toContain('Match all 40 games again')
    fireEvent.click(within(ask).getByRole('button', { name: 'Refresh' }))
    await waitFor(() => expect(toast()).toMatch(/^metadata done/))
  })

  it('offers only covers without credentials, and says so', async () => {
    await page()
    const actions = within(tab(/^Metadata and artwork/)).getByRole('group', {
      name: 'Metadata and artwork: actions',
    })
    expect(actions.textContent).toContain(
      'Without Twitch credentials only libretro covers are filled.',
    )
    expect(
      within(actions).getByRole('button', { name: 'Refresh Metadata' }).getAttribute('title'),
    ).toBe('Add Twitch credentials first')
  })

  it('locks a saved value until its edit icon opens it; Cancel or its undo locks it again', async () => {
    await page()
    const transports = tab(/^Transports and tools/)
    const staging = within(transports).getByRole('textbox', {
      name: 'Staging path on the device',
    }) as HTMLInputElement
    expect(staging.readOnly).toBe(true)
    fireEvent.click(
      within(transports).getByRole('button', { name: 'Change Staging path on the device' }),
    )
    expect(staging.readOnly).toBe(false)
    expect(document.activeElement).toBe(staging)
    fireEvent.change(staging, { target: { value: 'Elsewhere/{system}' } })
    fireEvent.click(within(transports).getByRole('button', { name: 'Cancel' }))
    expect(staging.readOnly).toBe(true)
    expect(staging.value).toBe('ROM-Sync/{system}')
    fireEvent.click(
      within(transports).getByRole('button', { name: 'Change Staging path on the device' }),
    )
    fireEvent.click(
      within(transports).getByRole('button', { name: 'Keep the saved Staging path on the device' }),
    )
    expect(staging.readOnly).toBe(true)
  })

  it('asks before upkeep that deletes, with what its dry run found', async () => {
    await page()
    const data = tab(/^Data and storage/)
    const covers = await within(data).findByRole('button', { name: 'Delete unreferenced covers' })
    await waitFor(() => expect(covers.hasAttribute('disabled')).toBe(false))
    fireEvent.click(covers)
    const ask = screen.getByRole('dialog', { name: 'Delete unreferenced covers' })
    expect(ask.textContent).toContain('3 items, 585.9 KB')
    act(() => fireEvent.click(within(ask).getByRole('button', { name: 'Run' })))
    await waitFor(() => expect(toast()).toBe('Delete unreferenced covers: started'))
  })

  it('follows a metadata pass that was running before the page opened, and stops it', async () => {
    render(<PassAlreadyRunning />)
    fireEvent.click(await screen.findByRole('tab', { name: 'Metadata and artwork' }))
    const ring = await screen.findByRole('progressbar', { name: 'Matching games' })
    expect(ring.getAttribute('aria-valuetext')).toBe('Matching games: 10 of 40')
    expect(screen.getByText('Alpha Quest')).toBeTruthy()
    const actions = screen.getByRole('group', { name: 'Metadata and artwork: actions' })
    expect(
      within(actions).getByRole('button', { name: 'Update Metadata' }).getAttribute('aria-busy'),
    ).toBe('true')
    fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
    await waitFor(() => expect(screen.queryByRole('progressbar')).toBeNull())
  })
})
