import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { PromptDialog } from './PromptDialog'

const meta = {
  title: 'Organisms/PromptDialog',
  component: PromptDialog,
  args: {
    title: 'Rename profile',
    label: 'Name',
    initial: 'Thor',
    submit: 'Rename',
    onSubmit: fn(),
    onCancel: fn(),
  },
} satisfies Meta<typeof PromptDialog>

export default meta
type Story = StoryObj<typeof meta>

export const Rename: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const field = canvas.getByRole('textbox', { name: 'Name' })
    await expect(field).toHaveFocus()
    await userEvent.clear(field)
    await userEvent.type(field, 'Thor Max{Enter}')
    await expect(args.onSubmit).toHaveBeenCalledWith('Thor Max')
  },
}
