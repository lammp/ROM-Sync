import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fireEvent, fn } from 'storybook/test'
import { Range } from './Range'

const meta = {
  title: 'Atoms/Range',
  component: Range,
  args: { label: 'Tiles', min: 90, max: 260, value: 150, onChange: fn() },
} satisfies Meta<typeof Range>

export default meta
type Story = StoryObj<typeof meta>

export const TileSize: Story = {
  play: async ({ canvas, args }) => {
    const slider = canvas.getByRole('slider', { name: 'Tiles' })
    slider.focus()
    await expect(slider).toHaveFocus()
    fireEvent.change(slider, { target: { value: '200' } })
    await expect(args.onChange).toHaveBeenCalledWith(200)
  },
}

export const RatingFloor: Story = {
  args: { label: 'Rating at least', min: 0, max: 100, value: 0, valueText: 'any' },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('slider', { name: 'Rating at least' })).toHaveAttribute(
      'aria-valuetext',
      'any',
    )
  },
}
