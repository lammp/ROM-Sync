import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SyncControl } from './SyncControl'

const reading = {
  pct: 42,
  eta: 95,
  phase: 'sending snes/Super Metroid.sfc',
  tip: '42.0 MB of 100.0 MB moved · sent 3 · removed 0 · failed 0 · 1.00 MB/s',
  totals: { bytes: 42 * 2 ** 20, sent: 3, removed: 0, freed: 0 },
  onDevice: 123,
  free: null,
  failed: 0,
}

const meta = {
  title: 'Molecules/SyncControl',
  component: SyncControl,
  args: { state: { kind: 'idle', onSync: fn() } },
} satisfies Meta<typeof SyncControl>

export default meta
type Story = StoryObj<typeof meta>

export const Idle: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Sync' }))
    if (args.state.kind === 'idle') await expect(args.state.onSync).toHaveBeenCalledOnce()
  },
}

export const NotConnected: Story = {
  args: { state: { kind: 'disabled', reason: 'Plug the device in to sync' } },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('button', { name: 'Sync' })).toBeDisabled()
    await expect(canvas.getByText('Plug the device in to sync')).toBeVisible()
  },
}

export const Starting: Story = { args: { state: { kind: 'running', reading: null } } }

export const Running: Story = {
  args: { state: { kind: 'running', reading } },
  play: async ({ canvas }) => {
    const status = canvas.getByRole('status')
    await expect(status).toHaveTextContent('42%')
    await expect(status).toHaveTextContent('ETA 2 min · sending snes/Super Metroid.sfc')
  },
}
