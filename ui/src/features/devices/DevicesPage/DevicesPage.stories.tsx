import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { useRouter, useSearchParams } from '@storybook/nextjs-vite/navigation.mock'
import type { ReadonlyURLSearchParams } from 'next/navigation'
import { expect, fn, mocked } from 'storybook/test'
import { fakeFetch, freshWorld } from '../../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../../../queries/engine/engine'
import { resetAppStore } from '../../../store/store'
import { DevicesPage } from './DevicesPage'

const search = (query: string) => new URLSearchParams(query) as unknown as ReadonlyURLSearchParams

const meta = {
  title: 'Features/Devices/DevicesPage',
  component: DevicesPage,
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
    mocked(useSearchParams).mockReturnValue(search(''))
  },
} satisfies Meta<typeof DevicesPage>

export default meta
type Story = StoryObj<typeof meta>

export const Every: Story = {
  play: async ({ canvas }) => {
    await expect(await canvas.findByRole('heading', { name: /^Devices/ })).toBeVisible()
  },
}

export const One: Story = {
  beforeEach: () => {
    mocked(useSearchParams).mockReturnValue(search('id=dev-1'))
  },
  play: async ({ canvas }) => {
    await expect(await canvas.findByRole('heading', { name: /^Thor/ })).toBeVisible()
  },
}
