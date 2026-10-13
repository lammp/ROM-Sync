import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, waitFor, within } from 'storybook/test'
import { fakeFetch, freshWorld, type World } from '../../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../../../queries/engine/engine'
import { resetAppStore } from '../../../store/store'
import { SettingsView } from './SettingsView'

const meta = {
  title: 'Features/Settings/SettingsView',
  component: SettingsView,
  decorators: [
    (Story, { parameters }) => {
      const world = freshWorld()
      if (parameters.shell) world.shell = parameters.shell as World['shell']
      // a library nothing has been looked up for yet, with credentials saved
      if (parameters.untouched)
        for (const g of world.games) Object.assign(g, { state: 'pending', matched: false })
      if (parameters.credentials) {
        world.stored['igdb.client_id'] = 'abcd1234'
        world.secret = 'a-saved-secret-of-thirty-chars'
      }
      return (
        <EngineProvider
          engine={createEngine({
            fetch: fakeFetch(world),
            baseUrl: 'http://engine.test',
            retry: 0,
            pollMs: 50,
          })}
        >
          <Story />
        </EngineProvider>
      )
    },
  ],
  parameters: { layout: 'fullscreen' },
  beforeEach: () => {
    resetAppStore()
    window.history.replaceState(null, '', window.location.pathname + window.location.search)
  },
} satisfies Meta<typeof SettingsView>

export default meta
type Story = StoryObj<typeof meta>

/**
 * Settings in tabs (F11-S48): the Library tab first; an edit marks its tab,
 * and Save in that tab saves it alone.
 */
export const FirstRun: Story = {
  play: async ({ canvas, userEvent }) => {
    await canvas.findByRole('tablist', { name: 'Settings groups' })
    await expect(canvas.getByRole('tab', { name: 'Library' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    await userEvent.click(canvas.getByRole('tab', { name: 'Transports and tools' }))
    const transports = canvas.getByRole('region', { name: /^Transports and tools/ })
    const probe = within(transports).getByRole('textbox', { name: 'Device probe interval' })
    await userEvent.clear(probe)
    await userEvent.type(probe, '30')
    await waitFor(() =>
      expect(
        canvas.getByRole('tab', { name: 'Transports and tools, unsaved changes' }),
      ).toBeVisible(),
    )
    await userEvent.click(
      within(transports).getByRole('button', { name: 'Save transports and tools' }),
    )
    await waitFor(() =>
      expect(
        within(transports).getByRole('button', { name: 'Save transports and tools' }),
      ).toBeDisabled(),
    )
    await expect(canvas.getByRole('tab', { name: 'Transports and tools' })).toBeVisible()
  },
}

/** In the desktop window (F12-S3): the page says so, and offers the chooser and Reveal. */
export const InTheDesktop: Story = {
  parameters: {
    shell: {
      kind: 'desktop',
      capabilities: ['reveal', 'pick_folder', 'browse_folders', 'open_url', 'notify'],
    },
  },
  play: async ({ canvas, userEvent }) => {
    const library = await canvas.findByRole('region', { name: /^Library/ })
    await expect(await within(library).findByRole('button', { name: /^ROMs folder/ })).toBeVisible()
    await expect(within(library).queryByRole('textbox', { name: 'ROMs folder' })).toBeNull()
    await userEvent.click(canvas.getByRole('tab', { name: 'Diagnostics' }))
    const diagnostics = canvas.getByRole('region', { name: /^Diagnostics/ })
    await waitFor(() => expect(diagnostics).toHaveTextContent('desktop window'))
  },
}

/** A browser reaching an engine bound off loopback: no shell action, and paths are typed. */
export const OffLoopback: Story = {
  parameters: { shell: { kind: 'browser', capabilities: [] } },
  play: async ({ canvas, userEvent }) => {
    await expect(await canvas.findByRole('textbox', { name: 'ROMs folder' })).toBeVisible()
    await expect(canvas.queryByRole('button', { name: /^Reveal/ })).toBeNull()
    await userEvent.click(canvas.getByRole('tab', { name: 'Diagnostics' }))
    const diagnostics = canvas.getByRole('region', { name: /^Diagnostics/ })
    await waitFor(() => expect(diagnostics).toHaveTextContent('browser'))
  },
}

/**
 * Choosing the store root by browsing (F11-S45): the field opens the folder
 * browser, a folder is opened and chosen, and Cancel puts back what is stored.
 */
export const ChooseByBrowsing: Story = {
  play: async ({ canvas, userEvent }) => {
    const library = await canvas.findByRole('region', { name: /^Library/ })
    const field = await within(library).findByRole('button', {
      name: 'ROMs folder D:\\Games\\ROMs Choose folder…',
    })
    await userEvent.click(field)
    const dialog = await canvas.findByRole('dialog', { name: 'Choose the ROMs folder' })
    await waitFor(() => expect(within(dialog).getByText('D:\\Games\\ROMs')).toBeVisible())
    await userEvent.click(within(dialog).getByRole('button', { name: 'Up' }))
    await userEvent.click(await within(dialog).findByRole('button', { name: '_firmware' }))
    await waitFor(() => expect(within(dialog).getByText('D:\\Games\\_firmware')).toBeVisible())
    await userEvent.click(within(dialog).getByRole('button', { name: 'Choose this folder' }))
    await expect(canvas.queryByRole('dialog')).toBeNull()
    await expect(
      within(library).getByRole('button', {
        name: 'ROMs folder D:\\Games\\_firmware Choose folder…',
      }),
    ).toBeVisible()
    await userEvent.click(within(library).getByRole('button', { name: 'Cancel' }))
    await expect(
      within(library).getByRole('button', { name: 'ROMs folder D:\\Games\\ROMs Choose folder…' }),
    ).toBeVisible()
  },
}

/**
 * The metadata's one action, at the top of its tab (F11-S52): Run Initial
 * while nothing is looked up, Update Metadata after, and Refresh Metadata,
 * which asks before it rebuilds.
 */
export const MetadataActions: Story = {
  parameters: { untouched: true, credentials: true },
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole('tab', { name: 'Metadata and artwork' }))
    const actions = canvas.getByRole('group', { name: 'Metadata and artwork: actions' })
    await userEvent.click(await within(actions).findByRole('button', { name: 'Run Initial' }))
    const update = await within(actions).findByRole('button', { name: 'Update Metadata' })
    await expect(update).toBeVisible()
    await userEvent.click(within(actions).getByRole('button', { name: 'Refresh Metadata' }))
    const ask = canvas.getByRole('dialog', { name: 'Refresh metadata' })
    await expect(ask).toHaveTextContent('a game you matched by hand keeps its match')
    await userEvent.click(within(ask).getByRole('button', { name: 'Refresh' }))
    await expect(canvas.queryByRole('dialog')).toBeNull()
  },
}
