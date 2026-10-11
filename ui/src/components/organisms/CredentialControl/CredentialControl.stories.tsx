import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { CredentialControl } from './CredentialControl'

const meta = {
  title: 'Organisms/CredentialControl',
  component: CredentialControl,
  args: {
    clientId: 'abcd1234',
    onClientId: fn(),
    secret: { present: true, length: 30, savedAt: '2026-10-08T04:11:00+00:00', source: 'typed' },
    draft: { kind: 'keep' },
    onDraft: fn(),
    test: { result: null, running: false, stale: false },
    onTest: fn(),
  },
} satisfies Meta<typeof CredentialControl>

export default meta
type Story = StoryObj<typeof meta>

export const Saved: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await expect(canvas.queryByLabelText('New client secret')).toBeNull()
    await userEvent.click(canvas.getByRole('button', { name: 'Replace' }))
    await expect(args.onDraft).toHaveBeenCalledWith({ kind: 'typed', text: '' })
  },
}

export const Imported: Story = {
  args: {
    secret: { present: true, length: 30, savedAt: '2026-10-08T04:11:00+00:00', source: 'imported' },
  },
}

export const Unset: Story = {
  args: { clientId: '', secret: { present: false, length: 0, savedAt: null, source: null } },
}

export const Typing: Story = { args: { draft: { kind: 'typed', text: 'short' } } }

export const Removing: Story = { args: { draft: { kind: 'remove' } } }

export const Tested: Story = {
  args: {
    test: {
      result: {
        ok: false,
        failedAt: 'token',
        stages: [{ name: 'token', outcome: 'failed', message: 'Twitch rejected the credentials' }],
      },
      running: false,
      stale: false,
    },
  },
}

export const TestedThenEdited: Story = {
  args: {
    test: {
      result: {
        ok: true,
        failedAt: null,
        stages: [
          { name: 'token', outcome: 'ok', message: null },
          { name: 'api', outcome: 'ok', message: null },
        ],
      },
      running: false,
      stale: true,
    },
  },
}
