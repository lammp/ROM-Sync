/**
 * The one client store (D22, F11-S6).
 *
 * Six slices in one Zustand container; server state lives in the query layer,
 * not here. Three things persist in the browser: under version 1's keys, the
 * device last chosen (`romsync.device`) and the facets opened or closed
 * (`romsync.facets`); and the notifications with the ids cleared
 * (`romsync.notices`). Storage can be missing or throw, so every read and
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
export const NOTICES_KEY = 'romsync.notices'

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
  try {
    const saved = JSON.parse(read(storage, NOTICES_KEY) ?? '{}') as {
      notices?: unknown
      cleared?: unknown
    }
    const { ui } = store.getState()
    store.setState({
      ui: {
        ...ui,
        notices: Array.isArray(saved.notices) ? (saved.notices as AppState['ui']['notices']) : [],
        cleared: Array.isArray(saved.cleared)
          ? saved.cleared.filter((c): c is string => typeof c === 'string')
          : [],
      },
    })
  } catch {
    // unreadable: no notifications kept
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
    if (now.ui.notices !== before.ui.notices || now.ui.cleared !== before.ui.cleared)
      write(
        storage,
        NOTICES_KEY,
        JSON.stringify({ notices: now.ui.notices, cleared: now.ui.cleared }),
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

const FIRST = appStore.getState()

/**
 * Puts the store back as the page found it, leaving storage alone: for tests
 * and stories, which share one store across many renders.
 */
export function resetAppStore(): void {
  // no notification carried over from what the browser kept: each test starts with none
  const kept = FIRST.ui.notices.length > 0 || FIRST.ui.cleared.length > 0
  appStore.setState(
    kept ? { ...FIRST, ui: { ...FIRST.ui, notices: [], cleared: [] } } : FIRST,
    true,
  )
}

/** Subscribes a component to the part of the state it selects, and nothing more. */
export function useAppStore<T>(selector: (state: AppState) => T): T {
  return useStore(appStore, selector)
}
