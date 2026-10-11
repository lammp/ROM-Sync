import { describe, expect, it } from 'vitest'
import { createStore } from 'zustand/vanilla'
import { uiSlice } from './ui'

const make = () => createStore(uiSlice)

describe('ui slice', () => {
  it('numbers toasts in order and dismisses one', () => {
    const store = make()
    const a = store.getState().ui.toast('Synced')
    const b = store.getState().ui.toast('Device is full', 'bad')
    expect([a, b]).toEqual([1, 2])
    store.getState().ui.dismiss(a)
    expect(store.getState().ui.toasts).toEqual([{ id: 2, text: 'Device is full', tone: 'bad' }])
    expect(store.getState().ui.toast('Again')).toBe(3)
  })

  it('opens one dialog at a time', () => {
    const store = make()
    store.getState().ui.openDialog('sync')
    store.getState().ui.openDialog('confirm')
    expect(store.getState().ui.dialog).toBe('confirm')
    store.getState().ui.closeDialog()
    expect(store.getState().ui.dialog).toBeNull()
  })

  it('shows and hides the compare card, and picks a system', () => {
    const store = make()
    store.getState().ui.compare(7)
    store.getState().ui.pickSystem('switch')
    expect([store.getState().ui.twin, store.getState().ui.system]).toEqual([7, 'switch'])
    store.getState().ui.compare(null)
    expect(store.getState().ui.twin).toBeNull()
  })
})
