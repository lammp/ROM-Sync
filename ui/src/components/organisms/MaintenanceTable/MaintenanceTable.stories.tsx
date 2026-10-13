import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { MaintenanceTable } from './MaintenanceTable'

const meta = {
  title: 'Organisms/MaintenanceTable',
  component: MaintenanceTable,
  args: {
    rows: [
      {
        action: 'prune-covers',
        label: 'Delete unreferenced covers',
        what: 'Covers no game points at.',
        count: 12,
        bytes: 3_400_000,
        onRun: fn(),
      },
      {
        action: 'clear-cache',
        label: 'Clear the screenshot cache',
        what: 'Screenshots fetch again when shown.',
        count: 0,
        bytes: 0,
        onRun: fn(),
      },
      {
        action: 'compact',
        label: 'Compact the database',
        what: 'Gives back space the database no longer uses.',
        count: null,
        bytes: 0,
        onRun: fn(),
      },
    ],
  },
} satisfies Meta<typeof MaintenanceTable>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Delete unreferenced covers' }))
    await expect(args.rows[0]?.onRun).toHaveBeenCalled()
  },
}

export const Busy: Story = { args: { busy: true } }
