import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { DeviceFigures } from './DeviceFigures'

const meta = {
  title: 'Molecules/DeviceFigures',
  component: DeviceFigures,
  args: { selected: 1284, onDevice: 1190, usedByGames: 96 * 2 ** 30 },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 14, width: 320 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof DeviceFigures>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByText('96.0 GB')).toBeVisible()
  },
}
