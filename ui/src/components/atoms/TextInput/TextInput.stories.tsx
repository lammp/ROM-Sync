import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { TextInput } from './TextInput'

const meta = {
  title: 'Atoms/TextInput',
  component: TextInput,
  args: { label: 'Store folder', value: 'D:\\Games\\ROMs', onChange: fn() },
  decorators: [(Story) => <div style={{ background: 'var(--bg2)', padding: 12 }}>{Story()}</div>],
} satisfies Meta<typeof TextInput>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const input = canvas.getByRole('textbox', { name: 'Store folder' })
    await userEvent.type(input, 'X')
    await expect(args.onChange).toHaveBeenLastCalledWith('D:\\Games\\ROMsX')
  },
}

export const Invalid: Story = {
  args: { value: 'not a folder', error: 'That folder does not exist.' },
  play: async ({ canvas }) => {
    const input = canvas.getByRole('textbox', { name: 'Store folder' })
    await expect(input).toBeInvalid()
    await expect(input).toHaveAccessibleDescription('That folder does not exist.')
  },
}

export const HiddenLabel: Story = { args: { hideLabel: true, label: 'New tag', value: '' } }

export const WithHelp: Story = {
  args: { help: 'The library every device is synced from.', error: 'That folder does not exist.' },
}
