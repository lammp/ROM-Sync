import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { StatRow } from './StatRow'

const meta = {
  title: 'Molecules/StatRow',
  component: StatRow,
  args: { label: 'Games', children: '8,214' },
  decorators: [
    (Story) => (
      <dl style={{ background: 'var(--bg2)', padding: 12, width: 300, margin: 0 }}>{Story()}</dl>
    ),
  ],
} satisfies Meta<typeof StatRow>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('definition')).toHaveTextContent('8,214')
  },
}
