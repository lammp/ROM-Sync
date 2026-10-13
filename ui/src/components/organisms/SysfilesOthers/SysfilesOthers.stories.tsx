import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SysfilesOthers } from './SysfilesOthers'

const meta = {
  title: 'Organisms/SysfilesOthers',
  component: SysfilesOthers,
  args: {
    stageRoot: 'ROM-Sync/bios',
    others: [
      { path: 'ROM-Sync/bios/gba', name: 'old_bios.bin', kind: 'file', size: 16384 },
      { path: 'ROM-Sync/bios', name: 'notes', kind: 'folder', size: null },
    ],
    onRemove: fn(),
  },
} satisfies Meta<typeof SysfilesOthers>

export default meta
type Story = StoryObj<typeof meta>

export const Stray: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Remove old_bios.bin' }))
    await expect(args.onRemove).toHaveBeenCalledWith(args.others[0])
  },
}

export const Removing: Story = { args: { busy: 'ROM-Sync/bios/gba/old_bios.bin' } }

export const NothingStray: Story = { args: { others: [] } }
