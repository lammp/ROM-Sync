import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { TwinGlyph } from './TwinGlyph'

const meta = {
  title: 'Atoms/TwinGlyph',
  component: TwinGlyph,
  args: { label: 'Also on 2 other systems' },
  decorators: [(Story) => <div style={{ background: 'var(--bg2)', padding: 12 }}>{Story()}</div>],
} satisfies Meta<typeof TwinGlyph>

export default meta
type Story = StoryObj<typeof meta>

export const Twin: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('img', { name: 'Also on 2 other systems' })).toBeVisible()
  },
}
export const Duplicate: Story = {
  args: { dupe: true, label: 'In the library twice on this system' },
}
