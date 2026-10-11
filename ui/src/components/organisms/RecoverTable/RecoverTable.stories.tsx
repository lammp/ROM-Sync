import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { RecoverTable } from './RecoverTable'

const meta = {
  title: 'Organisms/RecoverTable',
  component: RecoverTable,
  args: {
    device: 'Thor',
    items: [
      {
        system: 'snes',
        name: 'Hidden Gem (USA).sfc',
        kind: 'file',
        size: 2_097_152,
        fate: { kind: 'removed' },
      },
      {
        system: 'n64',
        name: 'Translation Patch',
        kind: 'folder',
        size: null,
        fate: { kind: 'left', why: 'Nintendo 64 is not managed on this device' },
      },
      {
        system: 'nes',
        name: 'Homebrew.nes',
        kind: 'file',
        size: 40_960,
        fate: { kind: 'left', why: 'nes is not a store system' },
      },
    ],
  },
} satisfies Meta<typeof RecoverTable>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('table', { name: 'On Thor, not in the store' })).toBeVisible()
  },
}

export const Nothing: Story = { args: { items: [] } }
