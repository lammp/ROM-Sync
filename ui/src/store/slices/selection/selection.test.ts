import { describe, expect, it } from 'vitest'
import { createStore } from 'zustand/vanilla'
import { selectionSlice } from './selection'

describe('selection slice', () => {
  it('chooses a device and forgets it, an empty reference meaning none', () => {
    const store = createStore(selectionSlice)
    expect(store.getState().selection.device).toBeNull()
    store.getState().selection.choose('ZmFrZQ')
    expect(store.getState().selection.device).toBe('ZmFrZQ')
    store.getState().selection.choose('')
    expect(store.getState().selection.device).toBeNull()
  })
})
