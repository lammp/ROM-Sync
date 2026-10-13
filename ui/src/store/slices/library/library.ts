/** How the library is laid out and which game the detail panel shows. */
import type { StateCreator } from 'zustand'
import { TILE, TILE_MAX, TILE_MIN } from '../../../design/tokens/tokens'

export type Layout = 'grid' | 'list'

export type LibrarySlice = {
  readonly library: {
    readonly layout: Layout
    readonly tile: number
    readonly current: number | null
    setLayout(layout: Layout): void
    setTile(px: number): void
    open(gameId: number): void
    close(): void
  }
}

export const librarySlice: StateCreator<LibrarySlice> = (set) => {
  const patch = (p: Partial<LibrarySlice['library']>) =>
    set((s) => ({ library: { ...s.library, ...p } }))
  return {
    library: {
      layout: 'grid',
      tile: TILE,
      current: null,
      setLayout: (layout) => patch({ layout }),
      setTile: (px) => patch({ tile: Math.min(TILE_MAX, Math.max(TILE_MIN, Math.round(px))) }),
      open: (gameId) => patch({ current: gameId }),
      close: () => patch({ current: null }),
    },
  }
}
