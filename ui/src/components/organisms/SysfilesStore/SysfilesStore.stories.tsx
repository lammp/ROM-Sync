import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { SysfilesStore } from './SysfilesStore'

const meta = {
  title: 'Organisms/SysfilesStore',
  component: SysfilesStore,
  args: {
    items: [
      {
        system: 'gba',
        label: 'Game Boy Advance',
        emulator: 'mGBA',
        name: 'gba_bios.bin',
        required: true,
        present: true,
        size: 16384,
        verified: true,
        note: '',
      },
      {
        system: 'ps2',
        label: 'PlayStation 2',
        emulator: 'NetherSX2',
        name: 'scph39001.bin',
        required: true,
        present: true,
        size: 4194304,
        verified: false,
        note: 'Any one region',
      },
      {
        system: 'nds',
        label: 'Nintendo DS',
        emulator: 'melonDS',
        name: 'bios7.bin',
        required: true,
        present: false,
        size: null,
        verified: null,
        note: '',
      },
    ],
  },
} satisfies Meta<typeof SysfilesStore>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('table', { name: 'System files in the store' })).toBeVisible()
  },
}

export const Empty: Story = { args: { items: [] } }
