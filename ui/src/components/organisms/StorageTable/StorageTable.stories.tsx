import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { StorageTable } from './StorageTable'

const MB = 1024 * 1024

const meta = {
  title: 'Organisms/StorageTable',
  component: StorageTable,
  args: {
    parts: [
      { component: 'database', files: 2, bytes: 40 * MB, reclaimable: 4 * MB },
      { component: 'covers', files: 1200, bytes: 300 * MB, reclaimable: 20 * MB },
      { component: 'cache', files: 80, bytes: 50 * MB, reclaimable: 50 * MB },
      { component: 'logs', files: 3, bytes: 2 * MB, reclaimable: 0 },
      { component: 'runs', files: 120, bytes: 8 * MB, reclaimable: 0 },
      { component: 'working', files: 0, bytes: 0, reclaimable: 0 },
      { component: 'webview', files: 400, bytes: 100 * MB, reclaimable: 0 },
    ],
  },
} satisfies Meta<typeof StorageTable>

export default meta
type Story = StoryObj<typeof meta>

export const Measured: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('table', { name: /^Storage:/ })).toBeVisible()
  },
}

export const NothingYet: Story = { args: { parts: [] } }
