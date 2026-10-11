import { describe, expect, it } from 'vitest'
import { createStore } from 'zustand/vanilla'
import { FRESH } from '../../../lib/progress/progress'
import { syncSlice } from './sync'

const MB = 1 << 20
const START = { bytesTotal: 60 * MB, removesTotal: 0, onDevice: 12, free: null }
const run = (id: string, bytes: number) => ({
  run: id,
  bytes_done: bytes,
  bytes_removed: 0,
  status: { state: 'running', sent: 1 },
})

describe('sync slice', () => {
  it('begins a run from a fixed start and finishes it', () => {
    const store = createStore(syncSlice)
    store.getState().sync.begin('job-1', 'dev', START)
    expect(store.getState().sync.running).toEqual({
      job: 'job-1',
      device: 'dev',
      start: START,
      tracker: FRESH,
      reading: null,
    })
    store.getState().sync.finish()
    expect(store.getState().sync.running).toBeNull()
  })

  it('keeps the tracker between polls, so runs are banked across them', () => {
    const store = createStore(syncSlice)
    store.getState().sync.begin('job-1', 'dev', START)
    store.getState().sync.poll(run('r1', 30 * MB), 0)
    store.getState().sync.poll(run('r2', 10 * MB), 1000)
    const running = store.getState().sync.running
    expect(running?.tracker.prev.bytes).toBe(30 * MB)
    expect(running?.reading?.totals.bytes).toBe(40 * MB)
    expect(running?.reading?.pct).toBe(66)
  })

  it('reads nothing when no sync is in flight', () => {
    const store = createStore(syncSlice)
    store.getState().sync.poll(run('r1', 1), 0)
    expect(store.getState().sync.running).toBeNull()
  })
})
