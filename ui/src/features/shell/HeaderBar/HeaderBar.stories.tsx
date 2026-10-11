import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { usePathname, useRouter } from '@storybook/nextjs-vite/navigation.mock'
import { expect, fn, mocked, waitFor } from 'storybook/test'
import { fakeFetch, freshWorld, seed } from '../../../../e2e/fake/world'
import { createEngine } from '../../../queries/engine/engine'
import { appStore, resetAppStore } from '../../../store/store'
import { Providers } from '../Providers/Providers'
import { HeaderBar } from './HeaderBar'

/** The fake engine's world, with a named state on top when a story asks for one. */
function world(scenario?: string) {
  const w = freshWorld()
  if (scenario) seed(w, scenario)
  return w
}

const meta = {
  title: 'Features/Shell/HeaderBar',
  component: HeaderBar,
  decorators: [
    (Story, { parameters }) => (
      <Providers
        engine={createEngine({
          fetch: fakeFetch(world(parameters.scenario as string | undefined)),
          baseUrl: 'http://engine.test',
          retry: 0,
        })}
      >
        <header
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            background: 'var(--bg2)',
            padding: '8px 14px',
          }}
        >
          <Story />
        </header>
      </Providers>
    ),
  ],
  beforeEach: () => {
    resetAppStore()
    mocked(usePathname).mockReturnValue('/')
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
} satisfies Meta<typeof HeaderBar>

export default meta
type Story = StoryObj<typeof meta>

export const OnTheLibrary: Story = {
  play: async ({ canvas, userEvent }) => {
    await expect(canvas.getByRole('link', { name: 'Library' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await waitFor(() =>
      expect(canvas.getAllByRole('option').map((o) => o.textContent)).toContain('Thor'),
    )
    await userEvent.selectOptions(canvas.getByRole('combobox', { name: 'Device' }), 'dev-1')
    await expect(appStore.getState().selection.device).toBe('dev-1')
    await waitFor(() =>
      expect(canvas.getByRole('img', { name: 'Thor is connected' })).toBeVisible(),
    )
    await userEvent.type(canvas.getByRole('searchbox'), 'star')
    await expect(appStore.getState().filters.query).toBe('star')
  },
}

/** A device plugged in holds something the store lacks: Recover joins the views. */
export const SomethingToRecover: Story = {
  parameters: { scenario: 'recover' },
  play: async ({ canvas }) => {
    await expect(await canvas.findByRole('link', { name: 'Recover' })).toBeVisible()
  },
}
