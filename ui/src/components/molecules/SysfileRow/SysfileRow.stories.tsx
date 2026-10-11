import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SysfileRow } from './SysfileRow'

const meta = {
  title: 'Molecules/SysfileRow',
  component: SysfileRow,
  args: { label: 'PlayStation', state: 'ready', count: 214, active: false, onSelect: fn() },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 6, width: 300 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof SysfileRow>

export default meta
type Story = StoryObj<typeof meta>

export const Ready: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: /PlayStation/ }))
    await expect(args.onSelect).toHaveBeenCalledOnce()
  },
}
export const Active: Story = { args: { active: true, state: 'missing' } }
export const NoGames: Story = { args: { count: 0, state: 'unseen' } }
export const Optional: Story = { args: { state: 'optional' } }
