import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SysfilesDetail, type SysfilesSystem } from './SysfilesDetail'

const gba: SysfilesSystem = {
  key: 'gba',
  label: 'Game Boy Advance',
  readiness: 'missing',
  emulator: 'mGBA',
  emulatorSeen: true,
  package: 'io.mgba.mgba',
  onDevice: { n: 120, bytes: 900 * 1024 * 1024 },
  inStore: 300,
  missing: ['gba_bios.bin'],
  note: '',
  staging: 'absent',
  stagingFolder: 'ROM-Sync/bios/gba',
  stagedAny: false,
  requirements: [
    {
      name: 'gba_bios.bin',
      stagedName: 'gba_bios.bin',
      note: 'The real BIOS; the built-in one skips the boot logo and breaks a few games.',
      required: true,
      group: false,
      store: { present: true, size: 16384, verified: true },
      staged: 'absent',
      installed: 'missing',
      installedPath: 'Android/data/io.mgba.mgba/files/bios',
    },
  ],
}

const meta = {
  title: 'Organisms/SysfilesDetail',
  component: SysfilesDetail,
  args: { system: gba, onStage: fn(), onUnstage: fn() },
} satisfies Meta<typeof SysfilesDetail>

export default meta
type Story = StoryObj<typeof meta>

export const Missing: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Add' }))
    await expect(args.onStage).toHaveBeenCalled()
    await expect(canvas.getByRole('button', { name: 'Remove' })).toBeDisabled()
  },
}

export const Outdated: Story = {
  args: {
    system: { ...gba, readiness: 'ready', missing: [], staging: 'outdated', stagedAny: true },
  },
}

export const Working: Story = { args: { busy: true } }

export const NothingNeeded: Story = {
  args: {
    system: {
      ...gba,
      key: 'snes',
      label: 'Super Nintendo',
      readiness: 'none',
      emulator: 'Snes9x',
      emulatorSeen: false,
      requirements: [],
      staging: 'nothing_to_stage',
      missing: [],
    },
  },
}
