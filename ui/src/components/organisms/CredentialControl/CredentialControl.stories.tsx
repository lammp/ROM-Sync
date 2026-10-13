import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { CredentialControl } from './CredentialControl'

const PASSED = {
  ok: true,
  failedAt: null,
  stages: [
    { name: 'token', outcome: 'ok', message: null },
    { name: 'api', outcome: 'ok', message: null },
  ],
}

const meta = {
  title: 'Organisms/CredentialControl',
  component: CredentialControl,
  args: {
    clientId: 'abcd1234',
    onClientId: fn(),
    clientLocked: true,
    onUnlockClient: fn(),
    secret: { present: true, length: 30, savedAt: '2026-10-08T04:11:00+00:00', source: 'typed' },
    draft: { kind: 'keep' },
    onDraft: fn(),
    test: { result: null, running: false, stale: false },
    onTest: fn(),
  },
} satisfies Meta<typeof CredentialControl>

export default meta
type Story = StoryObj<typeof meta>

/** Both saved: each locked, with its own way to change it. */
export const Saved: Story = {
  play: async ({ canvas, args, userEvent }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Change Twitch client ID' }))
    await expect(args.onUnlockClient).toHaveBeenCalledOnce()
    await userEvent.click(canvas.getByRole('button', { name: 'Enter a new client secret' }))
    await expect(args.onDraft).toHaveBeenCalledWith({ kind: 'typed', text: '' })
  },
}

/** A secret carried over from RomCurator says so. */
export const Imported: Story = {
  args: {
    secret: { present: true, length: 30, savedAt: '2026-10-08T04:11:00+00:00', source: 'imported' },
  },
}

/** Nothing saved: both fields open. */
export const Unset: Story = {
  args: {
    clientId: '',
    clientLocked: false,
    secret: { present: false, length: 0, savedAt: null, source: null },
  },
}

/** Testing: the recycle glyph turns. */
export const Testing: Story = { args: { test: { result: null, running: true, stale: false } } }

/** Passed: a tick on the button, and what passed beside it. */
export const Passed: Story = { args: { test: { result: PASSED, running: false, stale: false } } }

/** Failed: a cross on the button, and the stage that failed beside it. */
export const Failed: Story = {
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

/** Edited since the test: the result no longer applies, and the button is ready again. */
export const TestedThenEdited: Story = {
  args: { test: { result: PASSED, running: false, stale: true } },
}
