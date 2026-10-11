import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { useRouter } from '@storybook/nextjs-vite/navigation.mock'
import { expect, fn, mocked, waitFor, within } from 'storybook/test'
import { fakeFetch, freshWorld } from '../../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../../../queries/engine/engine'
import { resetAppStore } from '../../../store/store'
import { DevicesView } from './DevicesView'

const meta = {
  title: 'Features/Devices/DevicesView',
  component: DevicesView,
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
} satisfies Meta<typeof DevicesView>

export default meta
type Story = StoryObj<typeof meta>

/** Two profiles, one plugged in; a new drive, another computer's handheld, and one that cannot be read. */
export const EveryKind: Story = {
  play: async ({ canvas, userEvent }) => {
    const list = await canvas.findByRole('list', { name: 'Devices' })
    await waitFor(() => expect(within(list).getAllByRole('article')).toHaveLength(5))
    await expect(canvas.getByRole('img', { name: 'Thor is connected' })).toBeVisible()
    await expect(canvas.getByRole('img', { name: 'Deck card is not connected' })).toBeVisible()
    await userEvent.click(canvas.getByRole('button', { name: 'New profile…' }))
    const dialog = await canvas.findByRole('dialog', { name: 'New device profile' })
    await userEvent.type(within(dialog).getByRole('textbox', { name: 'Name' }), 'Card')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Create' }))
    await waitFor(() => expect(canvas.queryByRole('dialog')).toBeNull())
    await waitFor(() => expect(within(list).getAllByRole('article')).toHaveLength(5))
    await expect(canvas.getByRole('article', { name: 'Card' })).toBeVisible()
  },
}
