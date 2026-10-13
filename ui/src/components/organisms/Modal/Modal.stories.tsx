import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { Button } from '../../atoms/Button/Button'
import { Modal } from './Modal'

const meta = {
  title: 'Organisms/Modal',
  component: Modal,
  args: {
    title: 'Remove profile',
    onClose: fn(),
    children: (
      <>
        <p>Thor will be forgotten. Its games stay on the device.</p>
        <Button>Cancel</Button> <Button variant="danger">Remove</Button>
      </>
    ),
  },
} satisfies Meta<typeof Modal>

export default meta
type Story = StoryObj<typeof meta>

export const Open: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const dialog = canvas.getByRole('dialog', { name: 'Remove profile' })
    await expect(dialog).toHaveAttribute('aria-modal', 'true')
    await expect(canvas.getByRole('button', { name: 'Cancel' })).toHaveFocus()
    await userEvent.tab()
    await userEvent.tab()
    await expect(canvas.getByRole('button', { name: 'Close' })).toHaveFocus()
    await userEvent.tab()
    await expect(canvas.getByRole('button', { name: 'Cancel' })).toHaveFocus()
    await userEvent.keyboard('{Escape}')
    await expect(args.onClose).toHaveBeenCalledOnce()
  },
}

/** The close button in the corner closes it, as Escape and a click outside do. */
export const ClosedByItsButton: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Close' }))
    await expect(args.onClose).toHaveBeenCalledOnce()
  },
}
