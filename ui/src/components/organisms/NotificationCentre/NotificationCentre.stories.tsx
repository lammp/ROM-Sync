import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn, within } from 'storybook/test'
import { NotificationCentre, type NotificationItem } from './NotificationCentre'

const NOW = new Date(2026, 9, 13, 14, 30).getTime()
const MIN = 60_000

const NOTICES: NotificationItem[] = [
  {
    id: 'job:3',
    tone: 'bad',
    title: 'Sync to Thor failed',
    body: 'the device went away',
    at: NOW - 2 * MIN,
    read: false,
    href: '/devices',
  },
  {
    id: 'job:2',
    tone: 'info',
    title: 'Scan finished: 7,913 games found',
    body: '12 new',
    at: NOW - 30 * MIN,
    read: false,
    href: '/',
  },
  {
    id: 'setup:igdb',
    tone: 'info',
    title: 'Add IGDB credentials for covers and details',
    at: NOW - 26 * 60 * MIN,
    read: true,
    href: '/settings#metadata',
  },
]

const meta = {
  title: 'Organisms/NotificationCentre',
  component: NotificationCentre,
  args: {
    notices: NOTICES,
    now: NOW,
    onOpen: fn(),
    onClear: fn(),
    onClearAll: fn(),
    onFollow: fn(),
  },
  decorators: [
    (Story) => (
      <div style={{ display: 'flex', justifyContent: 'flex-end', padding: 12, minHeight: 360 }}>
        {Story()}
      </div>
    ),
  ],
} satisfies Meta<typeof NotificationCentre>

export default meta
type Story = StoryObj<typeof meta>

/** Two unread: the bell says so, and opening it lists all three, newest first. */
export const Unread: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const bell = canvas.getByRole('button', { name: 'Notifications, 2 unread' })
    await expect(bell).toHaveAttribute('aria-expanded', 'false')
    await userEvent.click(bell)
    await expect(args.onOpen).toHaveBeenCalledOnce()
    const panel = canvas.getByRole('dialog', { name: 'Notifications' })
    const items = within(panel).getAllByRole('listitem')
    await expect(items).toHaveLength(3)
    await expect(items[0]).toHaveTextContent('Error: Sync to Thor failed')
    await expect(items[0]).toHaveTextContent('the device went away')
    await expect(items[2]).toHaveTextContent('12 Oct')
  },
}

/** Clear one, clear all, and follow one to where it points. */
export const Clearing: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: /^Notifications/ }))
    await userEvent.click(
      canvas.getByRole('button', { name: 'Clear Scan finished: 7,913 games found' }),
    )
    await expect(args.onClear).toHaveBeenCalledWith('job:2')
    await userEvent.click(canvas.getAllByRole('button', { name: 'Open' })[0] as HTMLElement)
    await expect(args.onFollow).toHaveBeenCalledWith('/devices')
    await expect(canvas.queryByRole('dialog')).toBeNull()
    await userEvent.click(canvas.getByRole('button', { name: /^Notifications/ }))
    await userEvent.click(canvas.getByRole('button', { name: 'Clear all' }))
    await expect(args.onClearAll).toHaveBeenCalledOnce()
  },
}

/** Closes on its close button and on Escape, giving focus back to the bell. */
export const Closes: Story = {
  play: async ({ canvas, userEvent }) => {
    const bell = canvas.getByRole('button', { name: /^Notifications/ })
    await userEvent.click(bell)
    await userEvent.click(canvas.getByRole('button', { name: 'Close' }))
    await expect(canvas.queryByRole('dialog')).toBeNull()
    await expect(bell).toHaveFocus()
    await userEvent.click(bell)
    await userEvent.keyboard('{Escape}')
    await expect(canvas.queryByRole('dialog')).toBeNull()
  },
}

/** Nothing to report: the bell has no count. */
export const Empty: Story = {
  args: { notices: [] },
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Notifications' }))
    await expect(canvas.getByText('Nothing to report.')).toBeVisible()
  },
}
