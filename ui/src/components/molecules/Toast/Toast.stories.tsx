import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { Toast } from './Toast'

const meta = {
  title: 'Molecules/Toast',
  component: Toast,
  args: {
    toasts: [{ id: 1, text: 'Thor synced: sent 12, removed 3 (1.20 GB)', tone: 'info' }],
    onDismiss: fn(),
  },
} satisfies Meta<typeof Toast>

export default meta
type Story = StoryObj<typeof meta>

export const Info: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('status')).toHaveTextContent('Thor synced')
    await userEvent.click(canvas.getByRole('button', { name: 'Dismiss' }))
    await expect(args.onDismiss).toHaveBeenCalledWith(1)
  },
}

export const Problem: Story = {
  args: { toasts: [{ id: 2, text: 'Sync failed: the device went away', tone: 'bad' }] },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('status')).toHaveTextContent(
      'Problem: Sync failed: the device went away',
    )
  },
}

export const Empty: Story = { args: { toasts: [] } }
