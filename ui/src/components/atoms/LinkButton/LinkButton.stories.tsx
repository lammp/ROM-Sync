import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { LinkButton } from './LinkButton'

const meta = {
  title: 'Atoms/LinkButton',
  component: LinkButton,
  args: {
    href: '/api/v1/diagnostics/bundle',
    download: 'romsync-support.zip',
    children: 'Export a support bundle',
  },
} satisfies Meta<typeof LinkButton>

export default meta
type Story = StoryObj<typeof meta>

/** A download that looks like the tab's main action, and is a link. */
export const Download: Story = {
  args: { large: true },
  play: async ({ canvas }) => {
    const link = canvas.getByRole('link', { name: 'Export a support bundle' })
    await expect(link).toHaveAttribute('download', 'romsync-support.zip')
  },
}
