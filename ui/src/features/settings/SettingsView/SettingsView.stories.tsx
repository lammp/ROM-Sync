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
  beforeEach: () => resetAppStore(),
} satisfies Meta<typeof SettingsView>

export default meta
type Story = StoryObj<typeof meta>

/** First run with a store and its games, but no credentials: setup says what is left. */
export const FirstRun: Story = {
  play: async ({ canvas, userEvent }) => {
    const setup = await canvas.findByRole('list', { name: 'Setup' })
    await waitFor(() =>
      expect(within(setup).getAllByRole('listitem')[2]).toHaveTextContent('to do'),
    )
    const transports = canvas.getByRole('region', { name: /^Transports and tools/ })
    const probe = within(transports).getByRole('textbox', { name: 'Device probe interval' })
    await userEvent.clear(probe)
    await userEvent.type(probe, '30')
    await userEvent.click(
      within(transports).getByRole('button', { name: 'Save transports and tools' }),
    )
    await waitFor(() =>
      expect(
        within(transports).getByRole('button', { name: 'Save transports and tools' }),
      ).toBeDisabled(),
    )
  },
}

/** In the desktop window (F12-S3): the page says so, and offers Browse and Reveal. */
export const InTheDesktop: Story = {
  parameters: {
    shell: { kind: 'desktop', capabilities: ['reveal', 'pick_folder', 'open_url'] },
  },
  play: async ({ canvas }) => {
    const diagnostics = await canvas.findByRole('region', { name: /^Diagnostics/ })
    await waitFor(() => expect(diagnostics).toHaveTextContent('desktop window'))
    const library = canvas.getByRole('region', { name: /^Library/ })
    await expect(within(library).getByRole('button', { name: 'Browse…' })).toBeVisible()
  },
}

/** A browser reaching an engine bound off loopback: no shell action is offered. */
export const OffLoopback: Story = {
  parameters: { shell: { kind: 'browser', capabilities: [] } },
  play: async ({ canvas }) => {
    const diagnostics = await canvas.findByRole('region', { name: /^Diagnostics/ })
    await waitFor(() => expect(diagnostics).toHaveTextContent('browser'))
    await expect(canvas.queryByRole('button', { name: 'Browse…' })).toBeNull()
    await expect(canvas.queryByRole('button', { name: /^Reveal/ })).toBeNull()
  },
}
