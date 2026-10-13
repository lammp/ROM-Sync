import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { LibraryToolbar } from './LibraryToolbar'

const meta = {
  title: 'Organisms/LibraryToolbar',
  component: LibraryToolbar,
  args: {
    shown: { n: 245, bytes: 3 * 2 ** 30 },
    total: 8214,
    sort: 'title',
    onSort: fn(),
    view: 'grid',
    onView: fn(),
    tile: 150,
    onTile: fn(),
  },
} satisfies Meta<typeof LibraryToolbar>

export default meta
type Story = StoryObj<typeof meta>

export const Grid: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('status')).toHaveTextContent('245 of 8,214 · 3.00 GB')
    await userEvent.click(canvas.getByRole('button', { name: 'List' }))
    await expect(args.onView).toHaveBeenCalledWith('list')
  },
}

export const List: Story = { args: { view: 'list' } }
