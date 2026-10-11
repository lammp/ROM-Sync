import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { GameRow } from './GameRow'

const game = {
  id: 7,
  title: 'Super Metroid',
  name: 'Super Metroid (Japan, USA) (En,Ja).sfc',
  system: 'snes',
  sysLabel: 'Super Nintendo',
  year: 1994,
  rating: 93,
  size: 3_145_728,
  cover: null,
}

const meta = {
  title: 'Molecules/GameRow',
  component: GameRow,
  args: { game, current: false, onOpen: fn() },
  decorators: [(Story) => <div style={{ width: 760 }}>{Story()}</div>],
} satisfies Meta<typeof GameRow>

export default meta
type Story = StoryObj<typeof meta>

export const Plain: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Super Metroid' }))
    await expect(args.onOpen).toHaveBeenCalledOnce()
    await expect(canvas.getByText('3.00 MB')).toBeVisible()
  },
}

export const Current: Story = { args: { current: true } }

export const AllFourBadges: Story = {
  args: {
    current: true,
    device: { name: 'Thor', selected: false, override: true, onDevice: true, onToggle: fn() },
    twin: { dupe: false, label: 'Also on 1 other system: gba' },
  },
  play: async ({ canvas }) => {
    await expect(
      canvas.getByRole('button', { name: 'Super Metroid for Thor: not selected, chosen by hand' }),
    ).toBeVisible()
    await expect(canvas.getByText('on device')).toBeVisible()
  },
}
