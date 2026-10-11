import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { Chevron } from './Chevron'

const meta = {
  title: 'Atoms/Chevron',
  component: Chevron,
} satisfies Meta<typeof Chevron>

export default meta
type Story = StoryObj<typeof meta>

export const Expanded: Story = {
  play: async ({ canvasElement }) => {
    await expect(canvasElement.querySelector('[aria-hidden="true"]')).not.toBeNull()
  },
}
export const Collapsed: Story = { args: { collapsed: true } }
