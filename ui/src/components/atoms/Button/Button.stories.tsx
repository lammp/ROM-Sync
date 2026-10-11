import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { Button } from './Button'

const meta = {
  title: 'Atoms/Button',
  component: Button,
  args: { children: 'Scan library', onClick: fn() },
} satisfies Meta<typeof Button>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Scan library' }))
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}

export const Primary: Story = { args: { variant: 'primary', children: 'Sync now' } }

export const Danger: Story = { args: { variant: 'danger', children: 'Remove profile' } }

export const Active: Story = {
  args: { active: true, children: 'Grid' },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('button', { name: 'Grid', pressed: true })).toBeVisible()
  },
}

export const Small: Story = { args: { small: true, children: 'Accept' } }

export const Disabled: Story = {
  args: { disabled: true, children: 'Not connected' },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('button', { name: 'Not connected' })).toBeDisabled()
  },
}
