import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn, within } from 'storybook/test'
import { NewProfileDialog } from './NewProfileDialog'

const meta = {
  title: 'Organisms/NewProfileDialog',
  component: NewProfileDialog,
  args: {
    device: 'SD card (E:)',
    root: 'ROMs',
    drive: true,
    onCreate: fn(),
    onCancel: fn(),
  },
} satisfies Meta<typeof NewProfileDialog>

export default meta
type Story = StoryObj<typeof meta>

export const Empty: Story = {
  play: async ({ canvasElement, args, userEvent }) => {
    const dialog = within(canvasElement.ownerDocument.body).getByRole('dialog', {
      name: 'New device profile',
    })
    const create = within(dialog).getByRole('button', { name: 'Create' })
    await expect(create).toBeDisabled()
    await userEvent.type(within(dialog).getByRole('textbox', { name: 'Name' }), 'Card')
    await userEvent.click(within(dialog).getByRole('checkbox'))
    await userEvent.click(create)
    await expect(args.onCreate).toHaveBeenCalledWith('Card', false)
  },
}

export const Busy: Story = { args: { busy: true } }

export const Refused: Story = { args: { error: 'that device is not attached' } }
