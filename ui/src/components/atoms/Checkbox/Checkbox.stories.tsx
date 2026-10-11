import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { Checkbox } from './Checkbox'

const meta = {
  title: 'Atoms/Checkbox',
  component: Checkbox,
  args: { label: 'Only on the device', checked: false, onChange: fn() },
} satisfies Meta<typeof Checkbox>

export default meta
type Story = StoryObj<typeof meta>

export const Unchecked: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByText('Only on the device'))
    await expect(args.onChange).toHaveBeenCalledWith(true)
  },
}

export const Checked: Story = {
  args: { checked: true },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('checkbox', { name: 'Only on the device' })).toBeChecked()
  },
}

export const Disabled: Story = { args: { disabled: true } }
