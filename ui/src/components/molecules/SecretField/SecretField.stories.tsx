import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { useState } from 'react'
import { expect, fn } from 'storybook/test'
import { SecretField, type SecretDraft } from './SecretField'

const SAVED = { present: true, length: 30, savedAt: '2026-10-08T09:00:00Z', source: 'user' }
const NONE = { present: false, length: 0, savedAt: null, source: null }

const meta = {
  title: 'Molecules/SecretField',
  component: SecretField,
  args: {
    label: 'Client secret',
    stored: NONE,
    draft: { kind: 'keep' },
    onDraft: fn(),
    emptyHelp: 'Covers and details need Twitch credentials; libretro box art does not.',
  },
} satisfies Meta<typeof SecretField>

export default meta
type Story = StoryObj<typeof meta>

/** Nothing saved: an open field, with an eye to see what is typed. */
export const Empty: Story = {
  play: async ({ canvas, args, userEvent }) => {
    const field = canvas.getByLabelText('Client secret')
    await expect(field).toHaveAttribute('type', 'password')
    await userEvent.type(field, 'x')
    await expect(args.onDraft).toHaveBeenCalledWith({ kind: 'typed', text: 'x' })
  },
}

/** Saved: locked dots, with an icon to enter a new one and one to remove it. */
export const Saved: Story = {
  args: { stored: SAVED },
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByLabelText('Client secret')).toHaveAttribute('readonly')
    await expect(canvas.queryByRole('button', { name: 'Show the client secret' })).toBeNull()
    await userEvent.click(canvas.getByRole('button', { name: 'Enter a new client secret' }))
    await expect(args.onDraft).toHaveBeenCalledWith({ kind: 'typed', text: '' })
  },
}

/** A new one typed over a saved one: the eye shows it, and the saved one can be kept. */
export const Replacing: Story = {
  args: { stored: SAVED, draft: { kind: 'typed', text: 'short' } },
}

/** The saved one marked for removal, until the tab is saved. */
export const Removing: Story = { args: { stored: SAVED, draft: { kind: 'remove' } } }

/** The whole round: saved, opened, typed, shown, then kept after all. */
export const Round: Story = {
  args: { stored: SAVED },
  render: function Render(args) {
    const [draft, setDraft] = useState<SecretDraft>({ kind: 'keep' })
    return <SecretField {...args} draft={draft} onDraft={setDraft} />
  },
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Enter a new client secret' }))
    const field = canvas.getByLabelText('Client secret')
    await expect(field).toHaveFocus()
    await userEvent.type(field, 'a-new-secret')
    await userEvent.click(canvas.getByRole('button', { name: 'Show the client secret' }))
    await expect(field).toHaveAttribute('type', 'text')
    await userEvent.click(canvas.getByRole('button', { name: 'Keep the saved client secret' }))
    await expect(canvas.getByLabelText('Client secret')).toHaveAttribute('readonly')
  },
}
