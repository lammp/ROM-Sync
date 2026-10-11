import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { KeyValueText } from './KeyValueText'

const meta = {
  title: 'Atoms/KeyValueText',
  component: KeyValueText,
  args: { children: 'snes/Super Metroid (Japan, USA) (En,Ja).sfc' },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 200 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof KeyValueText>

export default meta
type Story = StoryObj<typeof meta>

export const Path: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByText(/Super Metroid/)).toBeVisible()
  },
}
