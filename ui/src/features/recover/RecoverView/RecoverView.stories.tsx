import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { fakeFetch, freshWorld, seed } from '../../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../../../queries/engine/engine'
import { resetAppStore } from '../../../store/store'
import { RecoverView } from './RecoverView'

function world(scenario: string | null) {
  const w = freshWorld()
  if (scenario) seed(w, scenario)
  return createEngine({ fetch: fakeFetch(w), baseUrl: 'http://engine.test', retry: 0 })
}

const meta = {
  title: 'Features/Recover/RecoverView',
  component: RecoverView,
  parameters: { layout: 'fullscreen' },
  beforeEach: () => resetAppStore(),
} satisfies Meta<typeof RecoverView>

export default meta
type Story = StoryObj<typeof meta>

/** Thor holds four items the library lacks. */
export const SomethingToRecover: Story = {
  decorators: [(Story) => <EngineProvider engine={world('recover')}>{Story()}</EngineProvider>],
  play: async ({ canvas }) => {
    await expect(
      await canvas.findByRole('table', { name: 'On Thor, not in the store' }),
    ).toBeVisible()
  },
}

/** Everything on the device is in the store. */
export const NothingToRecover: Story = {
  decorators: [(Story) => <EngineProvider engine={world(null)}>{Story()}</EngineProvider>],
  play: async ({ canvas }) => {
    await expect(
      await canvas.findByText('Everything on this device is in the store.'),
    ).toBeVisible()
  },
}
