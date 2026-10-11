import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { JobLine } from './JobLine'

const meta = {
  title: 'Molecules/JobLine',
  component: JobLine,
  args: {
    state: 'running',
    progress: { phase: 'scanning', done: 412, total: 8214, current: 'snes' },
  },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 360 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof JobLine>

export default meta
type Story = StoryObj<typeof meta>

export const Running: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('status')).toHaveTextContent('scanning 412 of 8,214 · snes')
  },
}
export const Done: Story = { args: { state: 'done', result: { added: 3, updated: 2, removed: 0 } } }
export const Failed: Story = {
  args: { state: 'failed', error: 'The store folder is not set.\nTraceback…' },
}
export const Queued: Story = { args: { state: 'queued' } }
