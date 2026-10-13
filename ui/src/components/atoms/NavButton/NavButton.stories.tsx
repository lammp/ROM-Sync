import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { NavButton } from './NavButton'

const meta = {
  title: 'Atoms/NavButton',
  component: NavButton,
  args: { href: '/devices', children: 'Devices' },
} satisfies Meta<typeof NavButton>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('link', { name: 'Devices' })).toHaveAttribute(
      'href',
      expect.stringMatching(/^\/devices\/?$/),
    )
  },
}

export const Current: Story = {
  args: { href: '/', children: 'Library', current: true },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('link', { name: 'Library' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  },
}
