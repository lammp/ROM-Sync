import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { SectionLabel } from './SectionLabel'

const meta = {
  title: 'Atoms/SectionLabel',
  component: SectionLabel,
  args: { children: 'Needs files' },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 6, width: 260 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof SectionLabel>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByText('Needs files')).toBeVisible()
  },
}
