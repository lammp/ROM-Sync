import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { useRouter } from '@storybook/nextjs-vite/navigation.mock'
import { expect, fn, mocked, waitFor, within } from 'storybook/test'
import { fakeFetch, freshWorld } from '../../../../e2e/fake/world'
import { EngineProvider, createEngine } from '../../../queries/engine/engine'
import { appStore, resetAppStore } from '../../../store/store'
import { LibraryView } from './LibraryView'

const meta = {
  title: 'Features/Library/LibraryView',
  component: LibraryView,
  decorators: [
    (Story) => (
      <EngineProvider
        engine={createEngine({
          fetch: fakeFetch(freshWorld()),
          baseUrl: 'http://engine.test',
          retry: 0,
        })}
      >
        <div style={{ height: 720, display: 'flex' }}>
          <Story />
        </div>
      </EngineProvider>
    ),
  ],
  parameters: { layout: 'fullscreen' },
  beforeEach: () => {
    resetAppStore()
    // The page navigates only to send a sync to the device's page; the router is a spy.
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
} satisfies Meta<typeof LibraryView>

export default meta
type Story = StoryObj<typeof meta>

/** No device chosen: the library to browse and filter, without selection. */
export const Browsing: Story = {
  play: async ({ canvas, userEvent }) => {
    await waitFor(() => expect(canvas.getByText(/^40 of 40/)).toBeVisible())
    await userEvent.click(canvas.getByRole('button', { name: /^Super Nintendo ?\d+$/ }))
    await waitFor(() => expect(canvas.getByText(/^10 of 40/)).toBeVisible())
    await expect(canvas.queryByRole('group', { name: /^Selection for/ })).toBeNull()
  },
}

/** Thor chosen: badges on every tile, the summary, and the bulk actions behind a dialog. */
export const CuratingForThor: Story = {
  beforeEach: () => {
    appStore.getState().selection.choose('dev-1')
    // The grid is windowed: a search brings the game into view.
    appStore.getState().filters.setQuery('star quest')
  },
  play: async ({ canvas, userEvent }) => {
    const summary = await canvas.findByRole('group', { name: 'Selection for Thor' })
    await waitFor(() => expect(summary).toHaveTextContent('11 selected'))
    await userEvent.click(
      await canvas.findByRole('button', { name: 'Star Quest 1 for Thor: selected' }),
    )
    await waitFor(() => expect(summary).toHaveTextContent('10 selected'))
    await userEvent.click(within(summary).getByRole('button', { name: 'Clear all' }))
    const dialog = await canvas.findByRole('dialog', { name: 'Clear the whole selection' })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Clear all' }))
    await waitFor(() => expect(summary).toHaveTextContent('0 selected'))
  },
}

/** A game open: its details, its tags with the proposal to decide, and its versions. */
export const GameOpen: Story = {
  beforeEach: () => {
    appStore.getState().library.open(1)
  },
  play: async ({ canvas }) => {
    const panel = await canvas.findByRole('article', { name: 'Star Quest 1' })
    await waitFor(() => expect(panel).toHaveTextContent('Space opera'))
    await expect(within(panel).getByRole('button', { name: 'Close details' })).toBeVisible()
  },
}
