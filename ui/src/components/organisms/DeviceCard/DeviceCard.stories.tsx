import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { DeviceCard, type ProfileCard } from './DeviceCard'

const GB = 1024 ** 3

const thor: ProfileCard = {
  variant: 'profile',
  name: 'Thor',
  online: true,
  transport: 'adb',
  roms: '/storage/emulated/0/ROMs',
  lastSeen: '2026-10-10T10:00:00',
  space: { total: 256 * GB, free: 120 * GB },
  figures: { selected: 1204, onDevice: 1180, usedByGames: 96 * GB },
  onSync: fn(),
  onContents: fn(),
  onChoose: fn(),
}

const meta = {
  title: 'Organisms/DeviceCard',
  component: DeviceCard,
  decorators: [(Story) => <div style={{ width: 340 }}>{Story()}</div>],
} satisfies Meta<typeof DeviceCard>

export default meta
type Story = StoryObj<typeof DeviceCard>

export const ProfileOnline: Story = {
  args: thor,
  play: async ({ canvas, userEvent }) => {
    await expect(canvas.getByRole('img', { name: 'Thor is connected' })).toBeVisible()
    await userEvent.click(canvas.getByRole('button', { name: 'Sync' }))
    await expect(thor.onSync).toHaveBeenCalled()
  },
}

export const ProfileOffline: Story = {
  args: { ...thor, online: false, space: null, figures: null },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('button', { name: 'Sync' })).toBeDisabled()
    await expect(canvas.getByText('offline · last seen 2026-10-10 10:00')).toBeVisible()
  },
}

export const CandidateNew: Story = {
  args: {
    variant: 'candidate',
    label: 'SD card (E:)',
    transport: 'volume',
    space: { total: 512 * GB, free: 500 * GB },
    state: { kind: 'new', onNew: fn() },
  },
}

export const CandidateForeign: Story = {
  args: {
    variant: 'candidate',
    label: 'Retroid (serial-2)',
    transport: 'adb',
    space: null,
    state: { kind: 'foreign', onAdopt: fn() },
  },
}

export const CandidateDebugging: Story = {
  args: {
    variant: 'candidate',
    label: 'Android device',
    transport: 'adb',
    space: null,
    state: { kind: 'debugging', reason: 'unauthorized' },
  },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('img', { name: 'Android device cannot be read' })).toBeVisible()
    await expect(canvas.queryByRole('button')).toBeNull()
  },
}
