import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { PasswordInput } from './PasswordInput'

const meta = {
  title: 'Atoms/PasswordInput',
  component: PasswordInput,
  args: { label: 'IGDB client secret', value: '', onChange: fn(), stored: true },
  decorators: [(Story) => <div style={{ background: 'var(--bg2)', padding: 12 }}>{Story()}</div>],
} satisfies Meta<typeof PasswordInput>

export default meta
type Story = StoryObj<typeof meta>

export const Stored: Story = {
  play: async ({ canvas }) => {
    const field = canvas.getByLabelText('IGDB client secret')
    await expect(field).toHaveValue('')
    await expect(field).toHaveAttribute('placeholder', 'Stored. Type to replace.')
  },
}

export const NotSet: Story = { args: { stored: false } }

export const Typing: Story = {
  args: { stored: false },
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.type(canvas.getByLabelText('IGDB client secret'), 'a')
    await expect(args.onChange).toHaveBeenLastCalledWith('a')
  },
}
