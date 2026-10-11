import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { DataTable } from './DataTable'

type Row = { system: string; games: number; size: string }

const meta = {
  title: 'Molecules/DataTable',
  component: DataTable<Row>,
  args: {
    caption: 'Systems on Thor',
    rowKey: (r: Row) => r.system,
    columns: [
      { key: 'system', label: 'System', cell: (r: Row) => r.system },
      { key: 'games', label: 'Games', numeric: true, cell: (r: Row) => r.games.toLocaleString() },
      { key: 'size', label: 'Size', numeric: true, cell: (r: Row) => r.size },
    ],
    rows: [
      { system: 'Super Nintendo', games: 412, size: '1.20 GB' },
      { system: 'Game Boy Advance', games: 1084, size: '9.80 GB' },
    ],
    empty: 'Nothing on the device yet.',
  },
} satisfies Meta<typeof DataTable<Row>>

export default meta
type Story = StoryObj<typeof meta>

export const Two: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('table', { name: 'Systems on Thor' })).toBeVisible()
    await expect(canvas.getByRole('cell', { name: '1,084' })).toBeVisible()
  },
}

export const Empty: Story = { args: { rows: [] } }
