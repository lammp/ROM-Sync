import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, waitFor } from 'storybook/test'
import { THOR_REF, answer, fakeFetch, freshWorld, type World } from '../../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../../../queries/engine/engine'
import { appStore, resetAppStore } from '../../../store/store'
import { SyncWatcher } from './SyncWatcher'

let world: World = freshWorld()

/** Thor's sync started in the engine and begun in the store, as the device page leaves it. */
function startThor(): void {
  world = freshWorld()
  const job = answer(world, 'POST', `/api/v1/devices/${THOR_REF}/sync`, {}).body as { id: string }
  resetAppStore()
  appStore
    .getState()
    .sync.begin(job.id, 'dev-1', { bytesTotal: 1, removesTotal: 0, onDevice: 1, free: null })
}

const meta = {
  title: 'Features/Shell/SyncWatcher',
  component: SyncWatcher,
  decorators: [
    (Story) => (
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
    ),
  ],
  beforeEach: startThor,
} satisfies Meta<typeof SyncWatcher>

export default meta
type Story = StoryObj<typeof meta>

/** It renders nothing: it moves the store's progress on and says when the sync ends. */
export const FollowsASync: Story = {
  play: async () => {
    await waitFor(() => expect(appStore.getState().sync.running).toBeNull())
    await expect(appStore.getState().ui.toasts.at(-1)?.text).toMatch(
      /^Thor synced: sent 10, removed 0/,
    )
  },
}
