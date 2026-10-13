import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { ActiveChipList } from './ActiveChipList'

const meta = {
  title: 'Molecules/ActiveChipList',
  component: ActiveChipList,
  args: {
    onClearAll: fn(),
    filters: [
      { key: 'system:snes', label: 'Super Nintendo', onRemove: fn() },
      { key: 'year', label: 'year 1990–1999', onRemove: fn() },
      { key: 'rating', label: 'rating ≥ 80', onRemove: fn() },
    ],
  },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 236 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof ActiveChipList>

export default meta
type Story = StoryObj<typeof meta>

export const Some: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Remove year 1990–1999' }))
    await expect(args.filters[1]?.onRemove).toHaveBeenCalledOnce()
    await userEvent.click(canvas.getByRole('button', { name: 'clear all' }))
    await expect(args.onClearAll).toHaveBeenCalledOnce()
  },
}

export const None: Story = { args: { filters: [] } }
