import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { GameTile } from './GameTile'

const COVER =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="400"><rect width="300" height="400"/></svg>',
  )

const game = {
  id: 7,
  title: 'Super Metroid',
  name: 'Super Metroid (Japan, USA) (En,Ja).sfc',
  system: 'snes',
  year: 1994,
  rating: 93,
  cover: null,
}

const meta = {
  title: 'Molecules/GameTile',
  component: GameTile,
  args: { game, current: false, onOpen: fn() },
  decorators: [(Story) => <div style={{ width: 150 }}>{Story()}</div>],
} satisfies Meta<typeof GameTile>

export default meta
type Story = StoryObj<typeof meta>

export const NoDevice: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: /Super Metroid/ }))
    await expect(args.onOpen).toHaveBeenCalledOnce()
    await expect(canvas.queryByRole('button', { pressed: true })).toBeNull()
  },
}

export const WithCover: Story = { args: { game: { ...game, cover: COVER } } }

export const Current: Story = { args: { current: true } }

export const AllFourBadges: Story = {
  args: {
    current: true,
    device: { name: 'Thor', selected: true, override: true, onDevice: true, onToggle: fn() },
    twin: { dupe: false, label: 'Also on 1 other system: gba' },
  },
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('img', { name: 'Also on 1 other system: gba' })).toBeVisible()
    await expect(canvas.getByText('on device')).toBeVisible()
    await userEvent.click(
      canvas.getByRole('button', { name: 'Super Metroid for Thor: selected, chosen by hand' }),
    )
    await expect(args.device?.onToggle).toHaveBeenCalledOnce()
    await expect(args.onOpen).not.toHaveBeenCalled()
  },
}

export const DuplicateSelected: Story = {
  args: {
    device: { name: 'Thor', selected: true, override: false, onDevice: false, onToggle: fn() },
    twin: { dupe: true, label: 'Already selected on gba' },
  },
}
