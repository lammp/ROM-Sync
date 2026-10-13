import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SelectionBadge } from './SelectionBadge'

const meta = {
  title: 'Atoms/SelectionBadge',
  component: SelectionBadge,
  args: {
    selected: false,
    override: false,
    title: 'Super Metroid',
    device: 'Thor',
    onToggle: fn(),
  },
  decorators: [(Story) => <div style={{ background: 'var(--bg3)', padding: 12 }}>{Story()}</div>],
} satisfies Meta<typeof SelectionBadge>

export default meta
type Story = StoryObj<typeof meta>

export const NotSelected: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const badge = canvas.getByRole('button', {
      name: 'Super Metroid for Thor: not selected',
      pressed: false,
    })
    await userEvent.click(badge)
    await expect(args.onToggle).toHaveBeenCalledOnce()
  },
}

export const Selected: Story = { args: { selected: true } }

export const SelectedByHand: Story = {
  args: { selected: true, override: true },
  play: async ({ canvas }) => {
    await expect(
      canvas.getByRole('button', {
        name: 'Super Metroid for Thor: selected, chosen by hand',
        pressed: true,
      }),
    ).toBeVisible()
  },
}

export const ExcludedByHand: Story = { args: { override: true } }
