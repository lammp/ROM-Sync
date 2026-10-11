import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { Chip } from './Chip'

const meta = {
  title: 'Atoms/Chip',
  component: Chip,
  args: { children: 'Platformer' },
  decorators: [(Story) => <div style={{ background: 'var(--bg2)', padding: 12 }}>{Story()}</div>],
} satisfies Meta<typeof Chip>

export default meta
type Story = StoryObj<typeof meta>

export const Plain: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.queryByRole('button')).toBeNull()
  },
}

export const Clickable: Story = {
  args: { kind: 'system', children: 'SNES', onClick: fn() },
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'SNES' }))
    await expect(args.onClick).toHaveBeenCalledOnce()
  },
}

export const Removable: Story = {
  args: { kind: 'franchise', children: 'Mario', onRemove: fn() },
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Remove Mario' }))
    await expect(args.onRemove).toHaveBeenCalledOnce()
  },
}

export const Suggested: Story = { args: { kind: 'suggested', children: 'Metroidvania' } }

export const EveryKind: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
      {(
        [
          'plain',
          'system',
          'franchise',
          'suggested',
          'collection',
          'theme',
          'mode',
          'perspective',
        ] as const
      ).map((kind) => (
        <Chip key={kind} kind={kind}>
          {kind}
        </Chip>
      ))}
    </div>
  ),
}
