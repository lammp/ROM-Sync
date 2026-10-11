import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SettingControl, type SettingDef } from './SettingControl'

const path: SettingDef = {
  kind: 'path',
  unit: '',
  minimum: null,
  maximum: null,
  choices: [],
  description: 'The store: the library every device is synced from.',
  restart: false,
}

const meta = {
  title: 'Molecules/SettingControl',
  component: SettingControl,
  args: { label: 'Store root', def: path, value: 'D:\\Games\\ROMs', onChange: fn() },
} satisfies Meta<typeof SettingControl>

export default meta
type Story = StoryObj<typeof meta>

export const Text: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.type(canvas.getByRole('textbox', { name: 'Store root' }), 'X')
    await expect(args.onChange).toHaveBeenLastCalledWith('D:\\Games\\ROMsX')
  },
}

export const Size: Story = {
  args: {
    label: 'Keep free on the device',
    def: {
      ...path,
      kind: 'int',
      unit: ' bytes',
      minimum: 0,
      maximum: 8 * 1024 ** 3,
      description: 'Headroom kept free after a sync.',
    },
    value: '512.0 MB',
    defaultText: '512.0 MB',
    onDefault: fn(),
  },
}

export const Invalid: Story = {
  args: {
    label: 'Preferred port',
    def: {
      ...path,
      kind: 'int',
      minimum: 0,
      maximum: 65535,
      restart: true,
      description: 'The port the window asks for.',
    },
    value: '70000',
    error: 'At most 65535',
  },
}

export const Flag: Story = {
  args: {
    label: 'Rescan on launch',
    def: { ...path, kind: 'bool', description: 'Read the store again each time the app starts.' },
    value: true,
  },
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('checkbox', { name: 'Rescan on launch' }))
    await expect(args.onChange).toHaveBeenCalledWith(false)
  },
}

export const Choice: Story = {
  args: {
    label: 'Log level',
    def: {
      ...path,
      kind: 'str',
      choices: ['debug', 'info', 'warning', 'error'],
      description: 'How much the log says.',
    },
    value: 'info',
  },
}
