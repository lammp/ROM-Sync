import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { AppShell } from './AppShell'

const meta = {
  title: 'Templates/AppShell',
  component: AppShell,
  args: {
    header: <span>ROM-Sync</span>,
    children: <p style={{ padding: 16 }}>The page</p>,
    toasts: <div role="status" aria-live="polite" />,
  },
  decorators: [(Story) => <div style={{ height: 320 }}>{Story()}</div>],
} satisfies Meta<typeof AppShell>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, userEvent }) => {
    await expect(canvas.getByRole('banner')).toHaveTextContent('ROM-Sync')
    await expect(canvas.getByRole('main')).toHaveTextContent('The page')
    await userEvent.tab()
    await expect(canvas.getByRole('link', { name: 'Skip to content' })).toHaveFocus()
  },
}
