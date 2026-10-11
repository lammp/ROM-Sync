import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { TwinRow } from './TwinRow'

const game = {
  title: "The Legend of Zelda: Majora's Mask 3D",
  name: "Legend of Zelda, The - Majora's Mask 3D (USA).3ds",
  sysLabel: 'Nintendo 3DS',
  year: 2015,
  size: 512 * 2 ** 20,
  cover: null,
}

const meta = {
  title: 'Molecules/TwinRow',
  component: TwinRow,
  args: { game, selected: false, onDevice: false, loose: false, action: { kind: 'none' } },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 10, width: 350 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof TwinRow>

export default meta
type Story = StoryObj<typeof meta>

export const ThisOne: Story = { args: { action: { kind: 'self' }, selected: true, onDevice: true } }

export const Switch: Story = {
  args: {
    loose: true,
    onOpen: fn(),
    action: { kind: 'switch', from: 'Nintendo 64', onSwitch: fn() },
  },
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByText('loose match')).toBeVisible()
    await userEvent.click(canvas.getByRole('button', { name: 'Switch' }))
    if (args.action.kind === 'switch') await expect(args.action.onSwitch).toHaveBeenCalledOnce()
  },
}

export const SelectAsWell: Story = {
  args: { onOpen: fn(), action: { kind: 'select', onSelect: fn() } },
}

export const Kept: Story = { args: { selected: true, onOpen: fn(), action: { kind: 'kept' } } }
