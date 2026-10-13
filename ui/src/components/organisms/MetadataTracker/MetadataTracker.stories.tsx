import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { MetadataTracker } from './MetadataTracker'

const COVERAGE = { total: 7913, matched: 564, pending: 7311, coverless: 7350 }

const meta = {
  title: 'Organisms/MetadataTracker',
  component: MetadataTracker,
  args: { coverage: COVERAGE, job: null, onStop: fn() },
} satisfies Meta<typeof MetadataTracker>

export default meta
type Story = StoryObj<typeof meta>

/** At rest: a ring of how much of the library is matched, and the counts beside it. */
export const AtRest: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('img', { name: '7% of the library matched' })).toBeVisible()
    await expect(canvas.queryByRole('button', { name: 'Stop' })).toBeNull()
  },
}

/** A pass running: the ring is its progress and turns; Stop is offered. */
export const Running: Story = {
  args: {
    job: {
      state: 'running',
      progress: { phase: 'match', done: 1234, total: 7311, current: 'Chrono Trigger' },
      result: null,
      error: null,
      started: '2026-10-13T10:00:00Z',
    },
  },
  play: async ({ canvas, args, userEvent }) => {
    const ring = canvas.getByRole('progressbar', { name: 'Matching games' })
    await expect(ring).toHaveAttribute('aria-valuenow', '17')
    await userEvent.click(canvas.getByRole('button', { name: 'Stop' }))
    await expect(args.onStop).toHaveBeenCalledOnce()
  },
}

/** Filling covers after the match. */
export const Covers: Story = {
  args: {
    job: {
      state: 'running',
      progress: { phase: 'covers', done: 40, total: 7350, current: 'Okami' },
      result: null,
      error: null,
      started: null,
    },
  },
}

/** Finished: a tick, and what it did. */
export const Finished: Story = {
  args: {
    job: {
      state: 'done',
      progress: null,
      result: { refresh: 0, matched: 7100, unmatched: 211, filled: 320 },
      error: null,
      started: null,
    },
  },
}

/** Failed: a cross, and why. */
export const Failed: Story = {
  args: {
    job: {
      state: 'failed',
      progress: null,
      result: null,
      error: 'stopped after 25 failures in a row; 40 of 7311 looked up',
      started: null,
    },
  },
}
