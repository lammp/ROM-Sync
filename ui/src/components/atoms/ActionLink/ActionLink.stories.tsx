import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { ActionLink } from './ActionLink'

const meta = {
  title: 'Atoms/ActionLink',
  component: ActionLink,
  args: { children: 'Show 50 more', onClick: fn() },
  decorators: [(Story) => <div style={{ background: 'var(--bg2)', padding: 12 }}>{Story()}</div>],
} satisfies Meta<typeof ActionLink>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Show 50 more' }))
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}

export const ByKeyboard: Story = {
  play: async ({ args, userEvent }) => {
    await userEvent.tab()
    await userEvent.keyboard('{Enter}')
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}
