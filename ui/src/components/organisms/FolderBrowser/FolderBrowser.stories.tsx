import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { FolderBrowser, type FolderListing } from './FolderBrowser'

const GAMES: FolderListing = {
  path: 'D:\\Games',
  parent: 'D:\\',
  folders: [
    { name: 'ROMs', path: 'D:\\Games\\ROMs' },
    { name: '_firmware', path: 'D:\\Games\\_firmware' },
  ],
  files: [],
}

const meta = {
  title: 'Organisms/FolderBrowser',
  component: FolderBrowser,
  args: {
    title: 'Choose the store folder',
    kind: 'folder',
    listing: GAMES,
    onOpen: fn(),
    onChoose: fn(),
    onCancel: fn(),
  },
} satisfies Meta<typeof FolderBrowser>

export default meta
type Story = StoryObj<typeof meta>

/** A folder shown: open a subfolder, go up, or choose the one shown. */
export const InAFolder: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('dialog', { name: 'Choose the store folder' })).toBeVisible()
    await expect(canvas.getByText('D:\\Games')).toBeVisible()
    await userEvent.click(canvas.getByRole('button', { name: 'ROMs' }))
    await expect(args.onOpen).toHaveBeenLastCalledWith('D:\\Games\\ROMs')
    await userEvent.click(canvas.getByRole('button', { name: 'Up' }))
    await expect(args.onOpen).toHaveBeenLastCalledWith('D:\\')
    await userEvent.click(canvas.getByRole('button', { name: 'Choose this folder' }))
    await expect(args.onChoose).toHaveBeenCalledWith('D:\\Games')
  },
}

/** The drives: nothing above them, and no drive list is itself a choice. */
export const Drives: Story = {
  args: {
    listing: {
      path: null,
      parent: null,
      folders: [
        { name: 'C:\\', path: 'C:\\' },
        { name: 'D:\\', path: 'D:\\' },
      ],
      files: [],
    },
  },
  play: async ({ canvas }) => {
    await expect(canvas.getByText('This computer')).toBeVisible()
    await expect(canvas.getByRole('button', { name: 'Up' })).toBeDisabled()
    await expect(canvas.getByRole('button', { name: 'Choose this folder' })).toBeDisabled()
    await expect(canvas.getByRole('list', { name: 'Drives' })).toBeVisible()
  },
}

/** Choosing a file: select it, then choose it. */
export const AFile: Story = {
  args: {
    title: 'Choose the ADB executable',
    kind: 'file',
    listing: {
      path: 'X:\\Tools\\platform-tools',
      parent: 'X:\\Tools',
      folders: [],
      files: [{ name: 'adb.exe', path: 'X:\\Tools\\platform-tools\\adb.exe' }],
    },
  },
  play: async ({ canvas, args, userEvent }) => {
    const choose = canvas.getByRole('button', { name: 'Choose this file' })
    await expect(choose).toBeDisabled()
    await userEvent.click(canvas.getByRole('button', { name: 'adb.exe' }))
    await expect(canvas.getByRole('button', { name: 'adb.exe' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    await userEvent.click(choose)
    await expect(args.onChoose).toHaveBeenCalledWith('X:\\Tools\\platform-tools\\adb.exe')
  },
}

/** A folder that cannot be listed: said, with a way back to the drives. */
export const Unreadable: Story = {
  args: {
    listing: undefined,
    error: 'D:\\Gone could not be opened: The system cannot find the path specified',
  },
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('alert')).toHaveTextContent('could not be opened')
    await userEvent.click(canvas.getByRole('button', { name: 'Show the drives' }))
    await expect(args.onOpen).toHaveBeenCalledWith(null)
  },
}

/** Every way out: Cancel, the close button, and Escape. */
export const Closes: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Cancel' }))
    await userEvent.click(canvas.getByRole('button', { name: 'Close' }))
    await userEvent.keyboard('{Escape}')
    await expect(args.onCancel).toHaveBeenCalledTimes(3)
  },
}
