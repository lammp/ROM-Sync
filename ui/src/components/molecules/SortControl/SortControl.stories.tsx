import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SortControl } from './SortControl'

const meta = {
  title: 'Molecules/SortControl',
  component: SortControl,
  args: { value: 'title', onChange: fn() },
} satisfies Meta<typeof SortControl>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.selectOptions(canvas.getByRole('combobox', { name: 'Sort' }), 'rating')
    await expect(args.onChange).toHaveBeenCalledWith('rating')
  },
}
