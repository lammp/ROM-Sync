import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { TextLink } from './TextLink'

const meta = {
  title: 'Atoms/TextLink',
  component: TextLink,
  args: { href: '/settings', children: 'Settings' },
  decorators: [
    (Story) => <p style={{ background: 'var(--bg2)', padding: 12 }}>Set the store in {Story()}.</p>,
  ],
} satisfies Meta<typeof TextLink>

export default meta
type Story = StoryObj<typeof meta>

export const Route: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('link', { name: 'Settings' })).toHaveAttribute(
      'href',
      expect.stringMatching(/^\/settings\/?$/),
    )
  },
}

export const External: Story = {
  args: { href: 'https://api-docs.igdb.com/', children: 'IGDB', external: true },
}
