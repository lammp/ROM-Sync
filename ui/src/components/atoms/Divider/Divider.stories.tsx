import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { Divider } from './Divider'

const meta = {
  title: 'Atoms/Divider',
  component: Divider,
} satisfies Meta<typeof Divider>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('separator')).toBeInTheDocument()
  },
}
