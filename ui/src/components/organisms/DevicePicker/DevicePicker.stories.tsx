import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { DevicePicker } from './DevicePicker'

const meta = {
  title: 'Organisms/DevicePicker',
  component: DevicePicker,
  args: {
    devices: [
      { id: 'dev-1', name: 'Thor', online: true },
      { id: 'dev-2', name: 'Card', online: false },
    ],
    value: 'dev-1',
    onChange: fn(),
  },
  decorators: [
    (Story) => (
      <div
        style={{
          display: 'flex',
          gap: 8,
          alignItems: 'center',
          background: 'var(--bg2)',
          padding: 12,
        }}
      >
        {Story()}
      </div>
    ),
  ],
} satisfies Meta<typeof DevicePicker>

export default meta
type Story = StoryObj<typeof meta>

export const Online: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('img', { name: 'Thor is connected' })).toBeVisible()
    await userEvent.selectOptions(canvas.getByRole('combobox', { name: 'Device' }), '')
    await expect(args.onChange).toHaveBeenCalledWith(null)
  },
}

export const None: Story = { args: { value: null } }
