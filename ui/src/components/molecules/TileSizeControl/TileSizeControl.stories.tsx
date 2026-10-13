import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { TileSizeControl } from './TileSizeControl'

const meta = {
  title: 'Molecules/TileSizeControl',
  component: TileSizeControl,
  args: { value: 150, onChange: fn() },
} satisfies Meta<typeof TileSizeControl>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('slider', { name: 'Tiles' })).toHaveAttribute(
      'aria-valuetext',
      '150 pixels wide',
    )
  },
}
