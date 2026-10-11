import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { FacetRow } from './FacetRow'

const meta = {
  title: 'Molecules/FacetRow',
  component: FacetRow,
  args: { label: 'Super Nintendo', count: 412, chosen: false, onToggle: fn() },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 260 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof FacetRow>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(
      canvas.getByRole('button', { name: 'Super Nintendo 412', pressed: false }),
    )
    await expect(args.onToggle).toHaveBeenCalledOnce()
  },
}
export const Chosen: Story = { args: { chosen: true } }
export const ChosenAtZero: Story = { args: { chosen: true, count: 0 } }
export const Zero: Story = { args: { count: 0 } }
