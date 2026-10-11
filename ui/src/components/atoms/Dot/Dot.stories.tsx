import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { Dot } from './Dot'

const meta = {
  title: 'Atoms/Dot',
  component: Dot,
} satisfies Meta<typeof Dot>

export default meta
type Story = StoryObj<typeof meta>

export const Neutral: Story = {}
export const Ok: Story = {
  args: { tone: 'ok', label: 'Ready' },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('img', { name: 'Ready' })).toBeVisible()
  },
}
export const Warn: Story = { args: { tone: 'warn', label: 'Partly ready' } }
export const Bad: Story = { args: { tone: 'bad', label: 'Missing files' } }
