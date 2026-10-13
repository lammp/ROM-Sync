import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { Muted } from './Muted'

const meta = {
  title: 'Atoms/Muted',
  component: Muted,
  args: { children: '1,284 games' },
} satisfies Meta<typeof Muted>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByText('1,284 games')).toBeVisible()
  },
}
