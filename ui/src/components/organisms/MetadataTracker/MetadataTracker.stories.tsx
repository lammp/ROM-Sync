import type { Meta, StoryObj } from '@storybook/nextjs-vite'
import { expect, fn } from 'storybook/test'
import { MetadataTracker } from './MetadataTracker'

const COVERAGE = { total: 7913, matched: 564, unmatched: 38, pending: 7311, coverless: 7350 }

const meta = {
  title: 'Organisms/MetadataTracker',
  component: MetadataTracker,
  args: { coverage: COVERAGE, job: null, onStop: fn() },
} satisfies Meta<typeof MetadataTracker>

export default meta
type Story = StoryObj<typeof meta>

/** Never run: a ring of how much of the library is matched, the counts beside it, and "Not run yet". */
export const AtRest: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByText('Not run yet')).toBeVisible()
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
      finished: null,
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
      finished: null,
    },
  },
}

/** Finished: a full ring and a tick, what the run did, and the library's coverage in words. */
export const Finished: Story = {
  args: {
    coverage: { total: 7913, matched: 7282, unmatched: 631, pending: 0, coverless: 121 },
    job: {
      state: 'done',
      progress: null,
      result: { refresh: 0, games: 7311, matched: 7100, unmatched: 211, filled: 320 },
      error: null,
      started: null,
      finished: '2026-10-14T09:05:00Z',
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
      finished: '2026-10-14T09:05:00Z',
    },
  },
}

/** Stopped by hand part way. */
export const Stopped: Story = {
  args: {
    job: {
      state: 'cancelled',
      progress: { phase: 'match', done: 300, total: 7311, current: null },
      result: null,
      error: null,
      started: '2026-10-14T08:00:00Z',
      finished: '2026-10-14T08:10:00Z',
    },
  },
}
