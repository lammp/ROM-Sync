import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { GridListToggle } from './GridListToggle'

const meta = {
  title: 'Molecules/GridListToggle',
  component: GridListToggle,
  args: { value: 'grid', onChange: fn() },
} satisfies Meta<typeof GridListToggle>

export default meta
type Story = StoryObj<typeof meta>

export const Grid: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('button', { name: 'Grid', pressed: true })).toBeVisible()
    await userEvent.click(canvas.getByRole('button', { name: 'List' }))
    await expect(args.onChange).toHaveBeenCalledWith('list')
  },
}
export const List: Story = { args: { value: 'list' } }
