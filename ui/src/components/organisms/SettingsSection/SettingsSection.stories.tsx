import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { SettingsSection } from './SettingsSection'

const meta = {
  title: 'Organisms/SettingsSection',
  component: SettingsSection,
  args: {
    id: 'library',
    title: 'Library',
    status: { tone: 'ok', word: '4 systems' },
    onSave: fn(),
    children: <p>Store root and rescan.</p>,
  },
} satisfies Meta<typeof SettingsSection>

export default meta
type Story = StoryObj<typeof meta>

export const Clean: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('button', { name: 'Save library' })).toBeDisabled()
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
