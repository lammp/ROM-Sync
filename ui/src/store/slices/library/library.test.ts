import { describe, expect, it } from 'vitest'
import { createStore } from 'zustand/vanilla'
import { TILE } from '../../../design/tokens/tokens'
import { TILE_MAX, TILE_MIN, librarySlice } from './library'

const make = () => createStore(librarySlice)

describe('library slice', () => {
  it('starts as a grid at the token tile size, with no game open', () => {
    const { layout, tile, current } = make().getState().library
    expect({ layout, tile, current }).toEqual({ layout: 'grid', tile: TILE, current: null })
  })

  it('switches layout and opens and closes a game', () => {
    const store = make()
    store.getState().library.setLayout('list')
    store.getState().library.open(42)
    expect(store.getState().library.layout).toBe('list')
    expect(store.getState().library.current).toBe(42)
    store.getState().library.close()
    expect(store.getState().library.current).toBeNull()
  })

  it('holds the tile size to whole pixels inside the slider range', () => {
    const store = make()
    store.getState().library.setTile(171.6)
    expect(store.getState().library.tile).toBe(172)
    store.getState().library.setTile(10)
    expect(store.getState().library.tile).toBe(TILE_MIN)
    store.getState().library.setTile(9999)
    expect(store.getState().library.tile).toBe(TILE_MAX)
  })
})
