import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, waitFor } from 'storybook/test'
import { answer, fakeFetch, freshWorld, type World } from '../../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../../../queries/engine/engine'
import { appStore, resetAppStore } from '../../../store/store'
import { NoticeWatcher } from './NoticeWatcher'

let world: World = freshWorld()

/** The world the story's engine answers from, for a test to change. */
export const worldNow = (): World => world

const meta = {
  title: 'Features/Shell/NoticeWatcher',
  component: NoticeWatcher,
  excludeStories: ['worldNow'],
  decorators: [
    (Story) => (
      <EngineProvider
        engine={createEngine({
          fetch: fakeFetch(world),
          baseUrl: 'http://engine.test',
          retry: 0,
          pollMs: 20,
        })}
      >
        <Story />
      </EngineProvider>
    ),
  ],
  beforeEach: () => {
    world = freshWorld()
    resetAppStore()
  },
} satisfies Meta<typeof NoticeWatcher>

export default meta
type Story = StoryObj<typeof meta>

/**
 * A setup step still to do is listed; a scan that ends while the page is open
 * is said and kept.
 */
export const SaysWhatHappens: Story = {
  play: async () => {
    await waitFor(() =>
      expect(appStore.getState().ui.notices.map((n) => n.id)).toContain('setup:igdb'),
    )
    answer(world, 'POST', '/api/v1/library/scan', {})
    await waitFor(() =>
      expect(appStore.getState().ui.notices[0]?.title).toMatch(/^Scan finished: \d+ games found$/),
    )
    await expect(appStore.getState().ui.toasts.at(-1)?.text).toMatch(/^Scan finished/)
  },
}
