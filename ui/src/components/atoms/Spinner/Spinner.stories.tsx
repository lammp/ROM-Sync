import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { Spinner } from './Spinner'

const meta = {
  title: 'Atoms/Spinner',
  component: Spinner,
} satisfies Meta<typeof Spinner>

export default meta
type Story = StoryObj<typeof meta>

export const Working: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('img', { name: 'Working' })).toBeVisible()
  },
}

export const Syncing: Story = { args: { label: 'Syncing' } }
