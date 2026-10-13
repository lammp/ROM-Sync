import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SegmentedControl } from './SegmentedControl'

const meta = {
  title: 'Molecules/SegmentedControl',
  component: SegmentedControl<'all' | 'none' | 'off'>,
  args: {
    label: 'Rule for Super Nintendo',
    value: 'all',
    onChange: fn(),
    segments: [
      { value: 'all', label: 'All' },
      { value: 'none', label: 'Pick' },
      { value: 'off', label: 'Off' },
    ],
  },
} satisfies Meta<typeof SegmentedControl<'all' | 'none' | 'off'>>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('radio', { name: 'All' })).toBeChecked()
    await userEvent.click(canvas.getByRole('radio', { name: 'Pick' }))
    await expect(args.onChange).toHaveBeenCalledWith('none')
  },
}

export const Disabled: Story = { args: { disabled: true } }
