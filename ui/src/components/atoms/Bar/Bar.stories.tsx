import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { Bar } from './Bar'

const meta = {
  title: 'Atoms/Bar',
  component: Bar,
  args: { value: 0.62, label: 'Space used' },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 240 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof Bar>

export default meta
type Story = StoryObj<typeof meta>

export const Partly: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('meter', { name: 'Space used' })).toHaveAttribute(
      'aria-valuenow',
      '62',
    )
  },
}
export const Empty: Story = { args: { value: 0 } }
export const Full: Story = { args: { value: 1, valueText: '512 GB of 512 GB' } }
export const Offline: Story = { args: { dim: true } }
