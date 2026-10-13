import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { IconButton } from './IconButton'

const meta = {
  title: 'Atoms/IconButton',
  component: IconButton,
  args: { label: 'Settings', children: '⚙', onClick: fn() },
} satisfies Meta<typeof IconButton>

export default meta
type Story = StoryObj<typeof meta>

export const Settings: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Settings' }))
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}

export const Close: Story = { args: { label: 'Close details', children: '×' } }

export const Active: Story = { args: { active: true } }
