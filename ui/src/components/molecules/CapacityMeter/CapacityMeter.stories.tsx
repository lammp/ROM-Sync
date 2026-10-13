import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { read, type CapacityInput } from '../../../lib/capacity/capacity'
import { CapacityMeter } from './CapacityMeter'

const GB = 2 ** 30
const settings = { warnFraction: 0.8, alarmFraction: 0.9, margin: GB / 2 }
const at = (
  free: number,
  net: number,
  fits: boolean | null = true,
  peak = Math.max(net, 0),
): CapacityInput => ({
  capacity: 128 * GB,
  free: free * GB,
  connected: true,
  selected: { n: 1284, bytes: 96 * GB },
  plan: { add: Math.max(net, 0), drop: 0, net, peak, fits },
})

const meta = {
  title: 'Molecules/CapacityMeter',
  component: CapacityMeter,
  args: { reading: read(at(64, 10 * GB), settings) },
  decorators: [(Story) => <div style={{ background: 'var(--bg)', padding: 12 }}>{Story()}</div>],
} satisfies Meta<typeof CapacityMeter>

export default meta
type Story = StoryObj<typeof meta>

export const Green: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('meter')).toHaveAttribute(
      'aria-valuetext',
      '58% used after sync, fits',
    )
    await expect(canvas.getByText('fits')).toBeVisible()
  },
}
export const Yellow: Story = { args: { reading: read(at(30, 6 * GB), settings) } }
export const Red: Story = { args: { reading: read(at(16, 5 * GB), settings) } }
export const Full: Story = {
  args: { reading: read(at(8, 4 * GB, false, 12 * GB), settings) },
  play: async ({ canvas }) => {
    await expect(canvas.getByText('will not fit')).toBeVisible()
    await expect(canvas.getByText(/short by 4.50 GB/)).toBeVisible()
  },
}
export const Unknown: Story = {
  args: { reading: read({ ...at(0, 0), capacity: null, connected: false }, settings) },
  play: async ({ canvas }) => {
    await expect(canvas.getByText(/capacity unknown \(not connected\)/)).toBeVisible()
  },
}
export const Live: Story = { args: { live: true, reading: read(at(40, 6 * GB), settings) } }
