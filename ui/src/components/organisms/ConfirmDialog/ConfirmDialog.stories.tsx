import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { ConfirmDialog } from './ConfirmDialog'

const meta = {
  title: 'Organisms/ConfirmDialog',
  component: ConfirmDialog,
  args: {
    title: 'Clear the selection',
    children:
      'Every game selected for Thor will be deselected. Nothing on the device changes until you sync.',
    confirm: 'Clear all',
    danger: true,
    onConfirm: fn(),
    onCancel: fn(),
  },
} satisfies Meta<typeof ConfirmDialog>

export default meta
type Story = StoryObj<typeof meta>

export const Danger: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('button', { name: 'Cancel' })).toHaveFocus()
    await userEvent.click(canvas.getByRole('button', { name: 'Clear all' }))
    await expect(args.onConfirm).toHaveBeenCalledOnce()
  },
}

export const Plain: Story = {
  args: {
    danger: false,
    title: 'Select shown',
    confirm: 'Select 214',
    children: 'Select the 214 games shown?',
  },
}
