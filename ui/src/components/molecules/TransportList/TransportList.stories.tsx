import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, within } from 'storybook/test'
import { TransportList } from './TransportList'

const meta = {
  title: 'Molecules/TransportList',
  component: TransportList,
  args: {
    transports: [
      { kind: 'volume', available: true, detail: '2 drive(s)' },
      { kind: 'mtp', available: true, detail: '1 storage(s)' },
      { kind: 'adb', available: true, detail: '1 device(s)' },
    ],
  },
} satisfies Meta<typeof TransportList>

export default meta
type Story = StoryObj<typeof meta>

export const AllFound: Story = {}

/** No adb on this computer: said as a state beside the others. */
export const WithoutAdb: Story = {
  args: {
    transports: [
      { kind: 'volume', available: true, detail: '2 drive(s)' },
      { kind: 'mtp', available: false, detail: 'turned off in Settings' },
      {
        kind: 'adb',
        available: false,
        detail: 'the Android debug bridge (adb) was not found on the PATH',
      },
    ],
  },
  play: async ({ canvas }) => {
    const items = within(canvas.getByRole('list', { name: 'Detected transports' })).getAllByRole(
      'listitem',
    )
    await expect(items[2]).toHaveTextContent('ADBnot available')
  },
}

/** Before the first probe answers, nothing is said. */
export const NotAskedYet: Story = { args: { transports: [] } }
