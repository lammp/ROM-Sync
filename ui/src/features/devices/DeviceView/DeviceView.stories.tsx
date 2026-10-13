import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { useRouter } from '@storybook/nextjs-vite/navigation.mock'
import { expect, fn, mocked, waitFor, within } from 'storybook/test'
import { fakeFetch, freshWorld } from '../../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../../../queries/engine/engine'
import { appStore, resetAppStore } from '../../../store/store'
import { DeviceView } from './DeviceView'

const meta = {
  title: 'Features/Devices/DeviceView',
  component: DeviceView,
  decorators: [
    (Story) => (
      <EngineProvider
        engine={createEngine({
          fetch: fakeFetch(freshWorld()),
          baseUrl: 'http://engine.test',
          retry: 0,
        })}
      >
        <Story />
      </EngineProvider>
    ),
  ],
  parameters: { layout: 'fullscreen' },
  args: { id: 'dev-1' },
  beforeEach: () => {
    resetAppStore()
    mocked(useRouter).mockReturnValue({
      push: fn(),
      replace: fn(),
      back: fn(),
      forward: fn(),
      refresh: fn(),
      prefetch: fn(),
      bfcacheId: 'story',
    })
  },
} satisfies Meta<typeof DeviceView>

export default meta
type Story = StoryObj<typeof meta>

/** Thor plugged in: its systems, what a sync would do, and the sync asked before it starts. */
export const Connected: Story = {
  play: async ({ canvas, canvasElement, userEvent }) => {
    await expect(await canvas.findByRole('heading', { name: /^Thor/ })).toBeVisible()
    await waitFor(() => expect(canvas.getByText(/Sync will/)).toBeVisible())
    await userEvent.click(canvas.getByRole('button', { name: 'Sync' }))
    const dialog = within(canvasElement.ownerDocument.body).getByRole('dialog', {
      name: 'Sync Thor',
    })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Start' }))
    await waitFor(() => expect(appStore.getState().sync.running?.device).toBe('dev-1'))
    await expect(canvas.getByRole('button', { name: 'Cancel sync' })).toBeVisible()
  },
}

/** A profile whose device is not plugged in: what it held when last seen, and nothing to sync. */
export const NotPluggedIn: Story = {
  args: { id: 'dev-2' },
  play: async ({ canvas }) => {
    await expect(await canvas.findByText('not plugged in')).toBeVisible()
    await expect(canvas.getByRole('button', { name: 'Sync' })).toBeDisabled()
    await expect(canvas.getByRole('button', { name: 'Scan device' })).toBeDisabled()
  },
}

export const Unknown: Story = {
  args: { id: 'dev-404' },
  play: async ({ canvas }) => {
    await expect(await canvas.findByRole('heading', { name: 'Device not found' })).toBeVisible()
  },
}
