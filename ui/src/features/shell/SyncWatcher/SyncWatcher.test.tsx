import { composeStories } from '@storybook/react'
import { render, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { THOR_REF } from '../../../../e2e/fake/world'
import { appStore } from '../../../store/store'
import { finishedText } from './SyncWatcher'
import * as stories from './SyncWatcher.stories'

const { FollowsASync } = composeStories(stories)

const job = (
  state: string,
  result: Record<string, number> | null,
  error: string | null = null,
) => ({
  id: 'j',
  kind: 'sync',
  target: THOR_REF,
  state,
  progress: null,
  result,
  error_code: error ? 'dest.unavailable' : null,
  error_message: error,
  started: null,
  finished: null,
})
const run = {
  id: 4,
  started: 'x',
  finished: 'y',
  state: 'done',
  counts: null,
  bytes_moved: 3 * 1024 * 1024,
}

describe('SyncWatcher', () => {
  it('follows the sync through its polls to the end, then says what it did', async () => {
    await FollowsASync.load()
    render(<FollowsASync />)
    await waitFor(() => expect(appStore.getState().sync.running?.reading).not.toBeNull())
    await waitFor(() => expect(appStore.getState().sync.running).toBeNull())
    const said = appStore.getState().ui.toasts.at(-1)
    expect(said).toMatchObject({ tone: 'info' })
    expect(said?.text).toMatch(/^Thor synced: sent 10, removed 0 \(/)
  })

  it('words each ending as version 1 did', () => {
    expect(
      finishedText('Thor', { job: job('done', { send: 2, update: 1, remove: 1 }), run }),
    ).toEqual({
      text: 'Thor synced: sent 3, removed 1 (3.00 MB)',
      bad: false,
    })
    expect(finishedText('Thor', { job: job('done', { send: 2, failed: 1 }), run: null })).toEqual({
      text: 'Thor synced: sent 2, removed 0, 1 failed',
      bad: true,
    })
    expect(finishedText('Thor', { job: job('failed', null, 'Thor went away'), run: null })).toEqual(
      {
        text: 'Sync failed: Thor went away',
        bad: true,
      },
    )
    expect(finishedText('Thor', { job: job('cancelled', { send: 1 }), run })).toEqual({
      text: 'Thor: sync cancelled after sent 1, removed 0 (3.00 MB)',
      bad: false,
    })
    expect(finishedText('Thor', { job: null, run: null }).bad).toBe(false)
  })
})
