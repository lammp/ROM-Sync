import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { Pill } from './Pill'

const meta = {
  title: 'Atoms/Pill',
  component: Pill,
  args: { children: 'queued' },
} satisfies Meta<typeof Pill>

export default meta
type Story = StoryObj<typeof meta>

export const Neutral: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByText('queued')).toBeVisible()
  },
}
export const Ok: Story = { args: { tone: 'ok', children: 'done' } }
export const Warn: Story = { args: { tone: 'warn', children: 'loose' } }
export const Bad: Story = { args: { tone: 'bad', children: 'failed' } }
