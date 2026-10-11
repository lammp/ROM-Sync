import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SyncControl } from '../../molecules/SyncControl/SyncControl'
import { SelectionSummary } from './SelectionSummary'

const meta = {
  title: 'Organisms/SelectionSummary',
  component: SelectionSummary,
  args: {
    device: { name: 'Thor', href: '/devices?id=dev-1' },
    selected: { n: 1284, bytes: 96 * 2 ** 30 },
    onDevice: 1190,
    shown: { selected: 214, unselected: 31 },
    sync: <SyncControl state={{ kind: 'idle', onSync: fn() }} />,
    onClearShown: fn(),
    onSelectShown: fn(),
    onClearAll: fn(),
    selectionKey: 1,
    onSettled: fn(),
  },
} satisfies Meta<typeof SelectionSummary>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Select shown (31)' }))
    await expect(args.onSelectShown).toHaveBeenCalledOnce()
    await expect(canvas.getByRole('link', { name: 'Thor' })).toBeVisible()
  },
}

export const NothingSelected: Story = {
  args: { selected: { n: 0, bytes: 0 }, shown: { selected: 0, unselected: 245 } },
}
