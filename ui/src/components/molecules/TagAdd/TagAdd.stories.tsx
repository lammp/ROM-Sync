import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { TagAdd } from './TagAdd'

const meta = {
  title: 'Molecules/TagAdd',
  component: TagAdd,
  args: { onAdd: fn() },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 388 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof TagAdd>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('button', { name: 'Add' })).toBeDisabled()
    await userEvent.type(
      canvas.getByRole('textbox', { name: 'Add a tag' }),
      'Franchise: Mortal Kombat{Enter}',
    )
    await expect(args.onAdd).toHaveBeenCalledWith({ kind: 'franchise', tag: 'Mortal Kombat' })
    await expect(canvas.getByRole('textbox', { name: 'Add a tag' })).toHaveValue('')
  },
}
