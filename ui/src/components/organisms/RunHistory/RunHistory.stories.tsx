import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { RunHistory } from './RunHistory'

const MB = 1 << 20

const meta = {
  title: 'Organisms/RunHistory',
  component: RunHistory,
  args: {
    runs: [
      {
        id: 12,
        started: '2026-10-10T21:04:11',
        state: 'failed',
        counts: { done: 40, failed: 2, send: 38, remove: 2 },
        bytesMoved: 3100 * MB,
      },
      {
        id: 11,
        started: '2026-10-08T19:30:00',
        state: 'done',
        counts: { done: 5, send: 3, update: 1, remove: 1 },
        bytesMoved: 420 * MB,
      },
      {
        id: 10,
        started: '2026-10-07T08:00:00',
        state: 'cancelled',
        counts: { done: 1, skipped: 9, send: 1 },
        bytesMoved: 12 * MB,
      },
    ],
  },
} satisfies Meta<typeof RunHistory>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('table', { name: 'History' })).toBeVisible()
  },
}

export const NoRuns: Story = { args: { runs: [] } }
