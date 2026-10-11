import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { FacetSection } from './FacetSection'

const rows = ['Nintendo Entertainment System', 'Super Nintendo', 'Game Boy'].map((name) => (
  <div key={name} style={{ padding: '2px 4px' }}>
    {name}
  </div>
))

const meta = {
  title: 'Molecules/FacetSection',
  component: FacetSection,
  args: { title: 'System', collapsed: false, onCollapsedChange: fn(), children: rows },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 260 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof FacetSection>

export default meta
type Story = StoryObj<typeof meta>

export const Open: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const toggle = canvas.getByRole('button', { name: 'System' })
    await expect(toggle).toHaveAttribute('aria-expanded', 'true')
    await userEvent.click(toggle)
    await expect(args.onCollapsedChange).toHaveBeenCalledWith(true)
  },
}

export const Collapsed: Story = {
  args: { collapsed: true },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('button', { name: 'System' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    await expect(canvas.queryByText('Super Nintendo')).not.toBeVisible()
  },
}

export const WithChosen: Story = {
  args: { chosen: 2, onClear: fn() },
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Clear System' }))
    await expect(args.onClear).toHaveBeenCalledOnce()
  },
}

export const MorePastTheFold: Story = {
  args: { fold: { hidden: 4, less: false, onToggle: fn() } },
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'more… (+4)' }))
    await expect(args.fold?.onToggle).toHaveBeenCalledOnce()
  },
}

export const Unfolded: Story = { args: { fold: { hidden: 0, less: true, onToggle: fn() } } }
