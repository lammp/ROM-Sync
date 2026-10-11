import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { VersionPicker } from './VersionPicker'

const meta = {
  title: 'Molecules/VersionPicker',
  component: VersionPicker,
  args: {
    current: 1,
    onPick: fn(),
    versions: [
      { id: 1, sysLabel: 'Nintendo 64', year: 2000, selected: true, loose: false },
      { id: 2, sysLabel: 'Nintendo 3DS', year: 2015, selected: false, loose: true },
    ],
  },
  decorators: [(Story) => <div style={{ background: 'var(--bg2)', padding: 12 }}>{Story()}</div>],
} satisfies Meta<typeof VersionPicker>

export default meta
type Story = StoryObj<typeof meta>

export const Two: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const picker = canvas.getByRole('combobox', { name: 'Version: in the library on 2 systems' })
    await userEvent.selectOptions(picker, '2')
    await expect(args.onPick).toHaveBeenCalledWith(2)
  },
}

export const One: Story = {
  args: {
    versions: [{ id: 1, sysLabel: 'Nintendo 64', year: 2000, selected: false, loose: false }],
  },
}
