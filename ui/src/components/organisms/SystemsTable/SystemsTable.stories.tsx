import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SystemsTable } from './SystemsTable'

const MB = 1 << 20

const meta = {
  title: 'Organisms/SystemsTable',
  component: SystemsTable,
  args: {
    rows: [
      {
        key: 'snes',
        label: 'Super Nintendo',
        store: { n: 812, bytes: 1900 * MB },
        device: { n: 800, bytes: 1880 * MB },
        mode: 'all',
        overrides: 12,
      },
      {
        key: 'gba',
        label: 'Game Boy Advance',
        store: { n: 300, bytes: 4200 * MB },
        device: { n: 4, bytes: 60 * MB },
        mode: 'none',
        overrides: 4,
      },
      {
        key: 'n64',
        label: 'Nintendo 64',
        store: { n: 120, bytes: 3000 * MB },
        device: { n: 0, bytes: 0 },
        mode: 'off',
        overrides: 0,
      },
      {
        key: 'saves',
        label: 'saves',
        store: null,
        device: { n: 3, bytes: 2 * MB },
        mode: 'off',
        overrides: 0,
      },
    ],
    onMode: fn(),
  },
} satisfies Meta<typeof SystemsTable>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const gba = canvas.getByRole('radiogroup', { name: 'Selection for Game Boy Advance' })
    await expect(gba).toBeVisible()
    await userEvent.click(canvas.getAllByRole('radio', { name: 'all' })[1] as HTMLElement)
    await expect(args.onMode).toHaveBeenCalledWith('gba', 'all')
  },
}

export const Busy: Story = { args: { disabled: true } }

export const Empty: Story = { args: { rows: [] } }
