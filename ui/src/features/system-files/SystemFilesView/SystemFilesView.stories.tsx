import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, waitFor, within } from 'storybook/test'
import { fakeFetch, freshWorld } from '../../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../../../queries/engine/engine'
import { appStore, resetAppStore } from '../../../store/store'
import { SystemFilesView } from './SystemFilesView'

const meta = {
  title: 'Features/SystemFiles/SystemFilesView',
  component: SystemFilesView,
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
} satisfies Meta<typeof SystemFilesView>

export default meta
type Story = StoryObj<typeof meta>

/** No device chosen: the store's copy of every file the registry knows. */
export const StoreOnly: Story = {
  play: async ({ canvas }) => {
    await expect(
      await canvas.findByRole('table', { name: 'System files in the store' }),
    ).toBeVisible()
  },
}

/** Thor chosen and plugged in: read the device, then stage what a system lacks. */
export const ForThor: Story = {
  beforeEach: () => {
    appStore.getState().selection.choose('dev-1')
  },
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(await canvas.findByRole('button', { name: 'Refresh from device' }))
    await waitFor(() => expect(canvas.getByText(/^device read/)).toBeVisible())
    await userEvent.click(canvas.getByRole('button', { name: /^Game Boy Advance/ }))
    const detail = canvas.getByRole('article', { name: /^Game Boy Advance/ })
    await userEvent.click(within(detail).getByRole('button', { name: 'Add' }))
    await waitFor(() =>
      expect(within(detail).getByText('current', { selector: 'dd' })).toBeVisible(),
    )
  },
}
