import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SysfilesList } from './SysfilesList'

const meta = {
  title: 'Organisms/SysfilesList',
  component: SysfilesList,
  decorators: [(Story) => <div style={{ width: 300 }}>{Story()}</div>],
  args: {
    systems: [
      { key: 'gba', label: 'Game Boy Advance', state: 'missing', count: 120 },
      { key: 'ps2', label: 'PlayStation 2', state: 'ready', count: 40 },
      { key: 'snes', label: 'Super Nintendo', state: 'none', count: 800 },
      { key: 'n64', label: 'Nintendo 64', state: 'unknown', count: 0 },
    ],
    others: 2,
    stageRoot: 'ROM-Sync/bios',
    active: 'gba',
    onSelect: fn(),
  },
} satisfies Meta<typeof SysfilesList>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: /^Other files/ }))
    await expect(args.onSelect).toHaveBeenCalledWith('*others')
  },
}

export const NothingStray: Story = { args: { others: 0, active: '*others' } }
