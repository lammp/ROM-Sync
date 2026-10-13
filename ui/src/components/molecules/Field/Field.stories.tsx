import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect } from 'storybook/test'
import { Field } from './Field'

const meta = {
  title: 'Molecules/Field',
  component: Field,
  args: {
    label: 'Port',
    help: 'The engine listens here, on this computer only.',
    children: ({ id, describedBy }) => (
      <input id={id} aria-describedby={describedBy} defaultValue="8765" />
    ),
  },
  decorators: [
    (Story) => <div style={{ background: 'var(--bg2)', padding: 12, width: 300 }}>{Story()}</div>,
  ],
} satisfies Meta<typeof Field>

export default meta
type Story = StoryObj<typeof meta>

export const WithHelp: Story = {
  play: async ({ canvas }) => {
    const input = canvas.getByLabelText('Port')
    await expect(input).toHaveAccessibleDescription(
      'The engine listens here, on this computer only.',
    )
  },
}

export const Bare: Story = { args: { help: undefined } }
