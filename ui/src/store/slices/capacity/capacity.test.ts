import { describe, expect, it } from 'vitest'
import { createStore } from 'zustand/vanilla'
import { capacitySlice } from './capacity'

describe('capacity slice', () => {
  it('warns once on each crossing into red or full', () => {
    const store = createStore(capacitySlice)
    const note = store.getState().capacity.note
    expect(note('d', 'green')).toBe(false)
    expect(note('d', 'yellow')).toBe(false)
    expect(note('d', 'red')).toBe(true)
    expect(note('d', 'red')).toBe(false)
    expect(note('d', 'full')).toBe(true)
    expect(note('d', 'green')).toBe(false)
    expect(note('d', 'red')).toBe(true)
  })

  it('keeps each device apart, and forgets one', () => {
    const store = createStore(capacitySlice)
    store.getState().capacity.note('a', 'red')
    expect(store.getState().capacity.note('b', 'red')).toBe(true)
    store.getState().capacity.forget('a')
    expect(store.getState().capacity.seen).toEqual({ b: 'red' })
    expect(store.getState().capacity.note('a', 'red')).toBe(true)
  })
})
