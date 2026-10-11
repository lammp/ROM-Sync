import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn, within } from 'storybook/test'
import { SyncConfirm } from './SyncConfirm'

const MB = 1 << 20
const op = (name: string, size: number) => ({ system: 'snes', name, size })

const meta = {
  title: 'Organisms/SyncConfirm',
  component: SyncConfirm,
  args: {
    name: 'Thor',
    plan: {
      send: [op('A.sfc', 3 * MB), op('B.sfc', 4 * MB)],
      update: [op('C.sfc', 2 * MB)],
      remove: [op('D.sfc', 1 * MB)],
      unchanged: 120,
      bytes: { net: 8 * MB, free: 1024 * MB },
    },
    onStart: fn(),
    onCancel: fn(),
  },
} satisfies Meta<typeof SyncConfirm>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvasElement, args, userEvent }) => {
    const dialog = within(canvasElement.ownerDocument.body).getByRole('dialog', {
      name: 'Sync Thor',
    })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Start' }))
    await expect(args.onStart).toHaveBeenCalled()
  },
}

export const SendOnly: Story = {
  args: {
    plan: {
      send: [op('A.sfc', 3 * MB)],
      update: [],
      remove: [],
      unchanged: 0,
      bytes: { net: 3 * MB, free: null },
    },
  },
}

export const Starting: Story = { args: { busy: true } }
