import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SearchInput } from '../../atoms/SearchInput/SearchInput'
import { AppHeader } from './AppHeader'

const meta = {
  title: 'Organisms/AppHeader',
  component: AppHeader,
  args: {
    nav: [
      { href: '/', label: 'Library', current: true },
      { href: '/devices', label: 'Devices', current: false },
      { href: '/system-files', label: 'System files', current: false },
    ],
    search: <SearchInput value="" onChange={fn()} />,
    devicePicker: <span>Thor</span>,
    settings: { href: '/settings', label: 'Settings', current: false },
  },
  decorators: [
    (Story) => (
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          background: 'var(--bg2)',
          padding: '8px 14px',
        }}
      >
        {Story()}
      </header>
    ),
  ],
} satisfies Meta<typeof AppHeader>

export default meta
type Story = StoryObj<typeof meta>

export const Library: Story = {
  play: async ({ canvas }) => {
    const nav = canvas.getByRole('navigation', { name: 'Main' })
    await expect(nav).toBeVisible()
    await expect(canvas.getByRole('link', { name: 'Library' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  },
}
