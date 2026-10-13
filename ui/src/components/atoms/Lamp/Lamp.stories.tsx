import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { Lamp } from './Lamp'

const meta = {
  title: 'Atoms/Lamp',
  component: Lamp,
  args: { state: 'off' },
  decorators: [(Story) => <div style={{ background: 'var(--bg2)', padding: 12 }}>{Story()}</div>],
} satisfies Meta<typeof Lamp>

export default meta
type Story = StoryObj<typeof meta>

export const Off: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('img', { name: 'Not connected' })).toBeVisible()
  },
}
export const On: Story = { args: { state: 'on' } }
export const Trouble: Story = { args: { state: 'bad', label: 'Device not writable' } }
