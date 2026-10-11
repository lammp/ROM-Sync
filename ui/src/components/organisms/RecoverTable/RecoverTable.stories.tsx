import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
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

/** Each file can be recovered; a folder cannot; a name the store has was refused. */
export const Recoverable: Story = {
  args: {
    onRecover: fn(),
    items: [
      {
        system: 'snes',
        name: 'Hidden Gem (USA).sfc',
        kind: 'file',
        size: 2_097_152,
        fate: { kind: 'removed' },
      },
      {
        system: 'snes',
        name: 'Clash (USA).sfc',
        kind: 'file',
        size: 1_048_576,
        fate: { kind: 'removed' },
        clash: true,
      },
      {
        system: 'n64',
        name: 'Translation Patch',
        kind: 'folder',
        size: null,
        fate: { kind: 'left', why: 'Nintendo 64 is not managed on this device' },
      },
    ],
  },
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Recover Hidden Gem (USA).sfc' }))
    await expect(args.onRecover).toHaveBeenCalledWith(args.items[0])
  },
}

export const Recovering: Story = {
  args: { ...Recoverable.args, busy: 'snes\\Hidden Gem (USA).sfc' },
}
