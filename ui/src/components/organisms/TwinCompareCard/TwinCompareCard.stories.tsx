import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { TwinCompareCard } from './TwinCompareCard'

const version = (title: string, sysLabel: string, year: number) => ({
  title,
  name: `${title}.rom`,
  sysLabel,
  year,
  size: 64 * 2 ** 20,
  cover: null,
})

const meta = {
  title: 'Organisms/TwinCompareCard',
  component: TwinCompareCard,
  args: {
    matchedOn: "The Legend of Zelda: Majora's Mask",
    onClose: fn(),
    rows: [
      {
        id: 1,
        game: version("Majora's Mask", 'Nintendo 64', 2000),
        selected: true,
        onDevice: true,
        loose: false,
        action: { kind: 'self' },
      },
      {
        id: 2,
        game: version("Majora's Mask 3D", 'Nintendo 3DS', 2015),
        selected: false,
        onDevice: false,
        loose: true,
        onOpen: fn(),
        action: { kind: 'switch', from: 'Nintendo 64', onSwitch: fn() },
      },
      {
        id: 3,
        game: version("Majora's Mask", 'GameCube', 2003),
        selected: false,
        onDevice: false,
        loose: false,
        onOpen: fn(),
        action: { kind: 'select', onSelect: fn() },
      },
    ],
  },
} satisfies Meta<typeof TwinCompareCard>

export default meta
type Story = StoryObj<typeof meta>

export const ByKeyboard: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const card = canvas.getByRole('dialog', { name: 'Same game on 2 other systems' })
    await expect(card).toHaveFocus()
    await userEvent.tab()
    await expect(canvas.getByRole('button', { name: 'Close comparison' })).toHaveFocus()
    await userEvent.tab()
    await userEvent.tab()
    await expect(canvas.getByRole('button', { name: 'Switch' })).toHaveFocus()
    await userEvent.keyboard('{Enter}')
    const row = args.rows[1]
    if (row?.action.kind === 'switch') await expect(row.action.onSwitch).toHaveBeenCalledOnce()
    await userEvent.keyboard('{Escape}')
    await expect(args.onClose).toHaveBeenCalledOnce()
  },
}

export const MatchedOnFileName: Story = { args: { matchedOn: null } }
