import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SMART_LISTS, SmartListButton } from './SmartListButton'

const meta = {
  title: 'Molecules/SmartListButton',
  component: SmartListButton,
  args: { ...SMART_LISTS[0]!, onApply: fn() },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 236 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof SmartListButton>

export default meta
type Story = StoryObj<typeof meta>

export const TopRated: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Top rated' }))
    await expect(args.onApply).toHaveBeenCalledWith('rating>85 votes>50')
  },
}
