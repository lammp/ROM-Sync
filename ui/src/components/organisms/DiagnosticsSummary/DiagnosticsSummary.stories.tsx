import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, within } from 'storybook/test'
import { DiagnosticsSummary } from './DiagnosticsSummary'

const meta = {
  title: 'Organisms/DiagnosticsSummary',
  component: DiagnosticsSummary,
  args: {
    version: 'ROM-Sync 2.0.0.dev0 · API v1',
    host: 'desktop window',
    address: 'http://127.0.0.1:8765/',
    bundleHref: '/api/v1/diagnostics/bundle',
    dataFolder: 'X:/LocalAppData/ROM-Sync/data',
    logFolder: 'X:/LocalAppData/ROM-Sync/data/logs',
    lastSync: {
      device: 'Thor',
      started: '2026-10-04T09:00:00',
      state: 'done',
      counts: { sent: 12, removed: 3 },
      bytes: 3 * 1024 * 1024 * 1024,
    },
    errors: [
      {
        job: 'j-7',
        kind: 'scan',
        finished: '2026-10-05T08:15:00',
        code: 'store.unreadable',
        message: 'the store folder could not be read',
      },
    ],
  },
} satisfies Meta<typeof DiagnosticsSummary>

export default meta
type Story = StoryObj<typeof meta>

export const Working: Story = {
  play: async ({ canvas }) => {
    const errors = canvas.getByRole('list', { name: 'Recent errors' })
    await expect(within(errors).getAllByRole('listitem')).toHaveLength(1)
  },
}

/** A first run: nothing synced, nothing failed. */
export const FirstRun: Story = {
  args: { lastSync: null, errors: [], host: 'browser' },
}
