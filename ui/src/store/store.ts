/**
 * The one client store (D22, F11-S6).
 *
 * Six slices in one Zustand container; server state lives in the query layer,
 * not here. Two things persist in the browser, under version 1's keys: the
 * device last chosen (`romsync.device`) and the facets opened or closed
 * (`romsync.facets`). Storage can be missing or throw, so every read and
 * write is guarded and the store works without it.
 */
import { useStore } from 'zustand'
import { createStore, type StoreApi } from 'zustand/vanilla'
import { capacitySlice, type CapacitySlice } from './slices/capacity/capacity'
import { FACETS, filtersSlice, type Facet, type FiltersSlice } from './slices/filters/filters'
import { librarySlice, type LibrarySlice } from './slices/library/library'
import { selectionSlice, type SelectionSlice } from './slices/selection/selection'
import { syncSlice, type SyncSlice } from './slices/sync/sync'
import { uiSlice, type UiSlice } from './slices/ui/ui'

export type AppState = LibrarySlice &
  FiltersSlice &
  SelectionSlice &
  SyncSlice &
  CapacitySlice &
  UiSlice
export type AppStore = StoreApi<AppState>
export type KeyValue = Pick<Storage, 'getItem' | 'setItem'>

export const SLICES = ['library', 'filters', 'selection', 'sync', 'capacity', 'ui'] as const
export const DEVICE_KEY = 'romsync.device'
export const FACETS_KEY = 'romsync.facets'

function read(storage: KeyValue | undefined, key: string): string | null {
  try {
    return storage?.getItem(key) ?? null
  } catch {
    return null
  }
}

function write(storage: KeyValue | undefined, key: string, value: string): void {
  try {
    storage?.setItem(key, value)
  } catch {
    // not available: the choice lasts for this page only
  }
}

function facetList(value: unknown): Facet[] {
  return Array.isArray(value) ? FACETS.filter((f) => value.includes(f)) : []
}

function restore(store: AppStore, storage: KeyValue | undefined): void {
  const device = read(storage, DEVICE_KEY)
  if (device) store.getState().selection.choose(device)
  try {
    const saved = JSON.parse(read(storage, FACETS_KEY) ?? '{}') as Record<string, unknown>
    const { filters } = store.getState()
    store.setState({
      filters: {
        ...filters,
        expanded: facetList(saved.expanded),
        collapsed: facetList(saved.collapsed),
      },
    })
  } catch {
    // unreadable: start fresh, as version 1 did
  }
}

export function createAppStore(storage?: KeyValue): AppStore {
  const store = createStore<AppState>()((...a) => ({
    ...librarySlice(...a),
    ...filtersSlice(...a),
    ...selectionSlice(...a),
    ...syncSlice(...a),
    ...capacitySlice(...a),
    ...uiSlice(...a),
  }))
  restore(store, storage)
  store.subscribe((now, before) => {
    if (now.selection.device !== before.selection.device)
      write(storage, DEVICE_KEY, now.selection.device ?? '')
    if (
      now.filters.expanded !== before.filters.expanded ||
      now.filters.collapsed !== before.filters.collapsed
    )
      write(
        storage,
        FACETS_KEY,
        JSON.stringify({ expanded: now.filters.expanded, collapsed: now.filters.collapsed }),
      )
  })
  return store
}

function browserStorage(): KeyValue | undefined {
  try {
    return typeof window === 'undefined' ? undefined : window.localStorage
  } catch {
    return undefined
  }
}

/** The application's store: the one container. */
export const appStore: AppStore = createAppStore(browserStorage())

/** Subscribes a component to the part of the state it selects, and nothing more. */
export function useAppStore<T>(selector: (state: AppState) => T): T {
  return useStore(appStore, selector)
}
