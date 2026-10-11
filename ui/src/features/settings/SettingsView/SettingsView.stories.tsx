import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, waitFor, within } from 'storybook/test'
import { fakeFetch, freshWorld } from '../../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../../../queries/engine/engine'
import { resetAppStore } from '../../../store/store'
import { SettingsView } from './SettingsView'

const meta = {
  title: 'Features/Settings/SettingsView',
  component: SettingsView,
  decorators: [
    (Story) => (
      <EngineProvider
        engine={createEngine({
          fetch: fakeFetch(freshWorld()),
          baseUrl: 'http://engine.test',
          retry: 0,
          pollMs: 50,
        })}
      >
        <Story />
      </EngineProvider>
    ),
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
