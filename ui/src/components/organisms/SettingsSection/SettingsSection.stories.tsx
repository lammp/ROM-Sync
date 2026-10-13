import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { Button } from '../../atoms/Button/Button'
import { SettingsSection } from './SettingsSection'

const meta = {
  title: 'Organisms/SettingsSection',
  component: SettingsSection,
  args: {
    id: 'library',
    title: 'Library',
    status: { tone: 'ok', word: '4 systems' },
    onSave: fn(),
    onCancel: fn(),
    children: <p>Store root and rescan.</p>,
  },
} satisfies Meta<typeof SettingsSection>

export default meta
type Story = StoryObj<typeof meta>

export const Clean: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('button', { name: 'Save library' })).toBeDisabled()
    await expect(canvas.getByRole('button', { name: 'Cancel' })).toBeDisabled()
  },
}

/** Edits dropped: Cancel puts back what is stored. */
export const Cancelled: Story = {
  args: { dirty: true },
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Cancel' }))
    await expect(args.onCancel).toHaveBeenCalledOnce()
    await expect(args.onSave).not.toHaveBeenCalled()
  },
}

export const Edited: Story = {
  args: { dirty: true },
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Save library' }))
    await expect(args.onSave).toHaveBeenCalled()
  },
}

export const Saving: Story = { args: { dirty: true, saving: true } }

export const Problem: Story = { args: { status: { tone: 'bad', word: 'no store chosen' } } }

export const NothingToSave: Story = { args: { onSave: undefined, status: undefined } }

/** Its main actions at its top, above its settings (F11-S51). */
export const WithActions: Story = {
  args: {
    actions: (
      <Button variant="primary" large>
        Rescan ROMs folder
      </Button>
    ),
  },
  play: async ({ canvas }) => {
    const actions = canvas.getByRole('group', { name: 'Library: actions' })
    await expect(actions).toContainElement(
      canvas.getByRole('button', { name: 'Rescan ROMs folder' }),
    )
  },
}

/** A graphic of the section's state beside its settings, where the section is wide (F11-S53). */
export const WithGraphic: Story = {
  args: {
    actions: (
      <Button variant="primary" large>
        Update Metadata
      </Button>
    ),
    aside: <p>The tracker</p>,
  },
}
