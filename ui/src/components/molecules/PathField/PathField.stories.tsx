import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { PathField } from './PathField'

const meta = {
  title: 'Molecules/PathField',
  component: PathField,
  args: {
    label: 'Store root',
    value: 'D:\\Games\\ROMs',
    kind: 'folder',
    help: 'The folder with one subfolder per system (nes, snes, psx and so on), laid out as ES-DE reads it.',
    onChoose: fn(),
    onChange: fn(),
  },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 640 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof PathField>

export default meta
type Story = StoryObj<typeof meta>

/** A chosen folder: the field is a button that opens the chooser. */
export const Chosen: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const field = canvas.getByRole('button', { name: 'Store root D:\\Games\\ROMs Choose folder…' })
    await expect(field).toHaveAccessibleDescription(
      'The folder with one subfolder per system (nes, snes, psx and so on), laid out as ES-DE reads it.',
    )
    await expect(canvas.queryByRole('textbox')).toBeNull()
    await userEvent.click(field)
    await expect(args.onChoose).toHaveBeenCalledOnce()
    await userEvent.click(canvas.getByRole('button', { name: 'clear store root' }))
    await expect(args.onChange).toHaveBeenCalledWith('')
  },
}

/** Nothing chosen yet: said in the field, and nothing to clear. */
export const NoneChosen: Story = {
  args: { value: '' },
  play: async ({ canvas }) => {
    await expect(
      canvas.getByRole('button', { name: 'Store root No folder chosen Choose folder…' }),
    ).toBeVisible()
    await expect(canvas.queryByRole('button', { name: /clear/ })).toBeNull()
  },
}

/** A file to choose, with the engine's refusal under it. */
export const FileWithError: Story = {
  args: {
    label: 'ADB executable',
    kind: 'file',
    value: 'X:\\Tools\\adb.exe',
    help: undefined,
    error: 'adb version failed: not an executable',
  },
  play: async ({ canvas }) => {
    const field = canvas.getByRole('button', {
      name: 'ADB executable X:\\Tools\\adb.exe Choose file…',
    })
    await expect(field).toHaveAttribute('data-invalid', 'true')
    await expect(field).toHaveAccessibleDescription('adb version failed: not an executable')
    await expect(canvas.getByText('Choose file…')).toBeVisible()
  },
}

/** Off loopback nothing can be chosen: the path is typed, and the field says why. */
export const Typed: Story = {
  args: { onChoose: undefined },
  play: async ({ canvas, args, userEvent }) => {
    const input = canvas.getByRole('textbox', { name: 'Store root' })
    await expect(input).toHaveAccessibleDescription(/can be chosen only on this computer/)
    await userEvent.type(input, 'x')
    await expect(args.onChange).toHaveBeenCalledWith('D:\\Games\\ROMsx')
  },
}
