import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { CardGrid } from './CardGrid'

const meta = {
  title: 'Templates/CardGrid',
  component: CardGrid,
  args: {
    label: 'Devices',
    children: ['Thor', 'Card'].map((n) => (
      <li key={n} style={{ background: 'var(--bg2)', padding: 14 }}>
        {n}
      </li>
    )),
  },
} satisfies Meta<typeof CardGrid>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getAllByRole('listitem')).toHaveLength(2)
  },
}

export const Wide: Story = { args: { min: 360, label: 'Settings' } }
