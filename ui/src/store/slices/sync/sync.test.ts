import { describe, expect, it } from 'vitest'
import { createStore } from 'zustand/vanilla'
import { ZERO, bankedTotal, syncSlice } from './sync'

const START = { free: 1000, onDevice: 12, at: '2026-10-11T00:00:00Z' }

describe('sync slice', () => {
  it('begins a run from a fixed start and finishes it', () => {
    const store = createStore(syncSlice)
    store.getState().sync.begin('job-1', 'dev', START)
    expect(store.getState().sync.running).toEqual({
      job: 'job-1',
      device: 'dev',
      start: START,
      banked: {},
    })
    store.getState().sync.finish()
    expect(store.getState().sync.running).toBeNull()
  })

  it('banks each run once by its id and totals them', () => {
    const store = createStore(syncSlice)
    store.getState().sync.begin('job-1', 'dev', START)
    store.getState().sync.bank('r1', { bytes: 10, removed: 1, copied: 2 })
    store.getState().sync.bank('r2', { bytes: 5, removed: 0, copied: 1 })
    store.getState().sync.bank('r2', { bytes: 7, removed: 0, copied: 1 })
    expect(bankedTotal(store.getState().sync.running)).toEqual({ bytes: 17, removed: 1, copied: 3 })
  })

  it('banks nothing when no run is in flight', () => {
    const store = createStore(syncSlice)
    store.getState().sync.bank('r1', { bytes: 10, removed: 1, copied: 2 })
    expect(store.getState().sync.running).toBeNull()
    expect(bankedTotal(null)).toEqual(ZERO)
  })
})
