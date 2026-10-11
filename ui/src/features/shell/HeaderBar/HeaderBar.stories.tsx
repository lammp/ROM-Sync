import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { usePathname, useRouter } from '@storybook/nextjs-vite/navigation.mock'
import { expect, fn, mocked, waitFor } from 'storybook/test'
import { fakeFetch, freshWorld } from '../../../../e2e/fake/world'
import { createEngine } from '../../../queries/engine/engine'
import { appStore, resetAppStore } from '../../../store/store'
import { Providers } from '../Providers/Providers'
import { HeaderBar } from './HeaderBar'

const meta = {
  title: 'Features/Shell/HeaderBar',
  component: HeaderBar,
  decorators: [
    (Story) => (
      <Providers
        engine={createEngine({
          fetch: fakeFetch(freshWorld()),
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
