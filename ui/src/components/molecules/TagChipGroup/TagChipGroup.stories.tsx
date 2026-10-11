import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { TagChipGroup } from './TagChipGroup'

const meta = {
  title: 'Molecules/TagChipGroup',
  component: TagChipGroup,
  args: {
    genres: ['Platform', 'Adventure'],
    tags: [
      { tag: 'Metroid', kind: 'franchise', state: 'accepted' },
      { tag: 'Science fiction', kind: 'theme', state: 'accepted' },
      { tag: 'Metroidvania', kind: 'user', state: 'proposed' },
    ],
    onRemove: fn(),
    onDecide: fn(),
  },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 388 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof TagChipGroup>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Accept Metroidvania' }))
    await expect(args.onDecide).toHaveBeenCalledWith(args.tags[2], true)
    await userEvent.click(canvas.getByRole('button', { name: 'Remove Metroid' }))
    await expect(args.onRemove).toHaveBeenCalledWith(args.tags[0])
  },
}

export const GenresOnly: Story = { args: { tags: [] } }
