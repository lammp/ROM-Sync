import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { useState } from 'react'
import { expect, fn } from 'storybook/test'
import { LockedField } from './LockedField'

const meta = {
  title: 'Molecules/LockedField',
  component: LockedField,
  args: {
    label: 'Twitch client ID',
    value: 'abc123clientid',
    locked: true,
    onChange: fn(),
    onUnlock: fn(),
    help: 'From the Twitch developer console.',
  },
} satisfies Meta<typeof LockedField>

export default meta
type Story = StoryObj<typeof meta>

/** Saved: shown, not editable, with an edit icon at its end. */
export const Locked: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.getByRole('textbox', { name: 'Twitch client ID' })).toHaveAttribute(
      'readonly',
    )
    await userEvent.click(canvas.getByRole('button', { name: 'Change Twitch client ID' }))
    await expect(args.onUnlock).toHaveBeenCalledOnce()
  },
}

/** Empty: open, with nothing to unlock. */
export const Empty: Story = { args: { value: '', locked: false } }

/** Opened by its edit icon: editable, and the caret is in it. */
export const Opened: Story = {
  render: function Render(args) {
    const [locked, setLocked] = useState(true)
    const [value, setValue] = useState(args.value)
    return (
      <LockedField
        {...args}
        value={value}
        locked={locked}
        onUnlock={() => setLocked(false)}
        onLock={() => {
          setValue(args.value)
          setLocked(true)
        }}
        onChange={setValue}
      />
    )
  },
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Change Twitch client ID' }))
    const field = canvas.getByRole('textbox', { name: 'Twitch client ID' })
    await expect(field).toHaveFocus()
    await expect(field).not.toHaveAttribute('readonly')
  },
}

/** A value the engine refused, said under the field. */
export const Refused: Story = { args: { locked: false, error: 'Must contain {system}' } }
