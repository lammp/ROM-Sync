import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { check, readTree } from '../../structure/layering/layering'
import {
  DEVICE_KEY,
  FACETS_KEY,
  SLICES,
  appStore,
  createAppStore,
  resetAppStore,
  type KeyValue,
} from './store'

const SRC = join(import.meta.dirname, '..')

class Memory implements KeyValue {
  readonly items = new Map<string, string>()
  getItem(key: string) {
    return this.items.get(key) ?? null
  }
  setItem(key: string, value: string) {
    this.items.set(key, value)
  }
}

const broken: KeyValue = {
  getItem: () => {
    throw new Error('denied')
  },
  setItem: () => {
    throw new Error('denied')
  },
}

describe('store', () => {
  it('single_container', () => {
    expect(Object.keys(createAppStore().getState()).sort()).toEqual([...SLICES].sort())
    const tree = readTree(SRC)
    const makers = Object.entries(tree).filter(
      ([file, source]) =>
        !/\.test\.tsx?$/.test(file) &&
        /from 'zustand(\/vanilla)?'/.test(source) &&
        /\bcreateStore\b|\bcreate\(/.test(source),
    )
    expect(makers.map(([file]) => file)).toEqual(['store/store.ts'])
    const importers = Object.entries(tree)
      .filter(([file, source]) => !file.startsWith('store/') && /from 'zustand/.test(source))
      .map(([file]) => file)
    expect(importers).toEqual([])
  })

  it('no_module_state', () => {
    expect(check(readTree(SRC)).filter((v) => v.rule === 'module-state')).toEqual([])
  })

  it('resets to the state the page found, actions included', () => {
    const first = appStore.getState()
    appStore.getState().filters.setQuery('quest')
    appStore.getState().selection.choose('dev-9')
    resetAppStore()
    expect(appStore.getState()).toBe(first)
    expect(appStore.getState().filters.query).toBe('')
  })

  it('is one store whose slices share it', () => {
    const store = createAppStore()
    store.getState().selection.choose('dev')
    store.getState().filters.setQuery('mario')
    expect(store.getState().selection.device).toBe('dev')
    expect(store.getState().filters.query).toBe('mario')
    expect(appStore.getState()).toHaveProperty('library')
  })

  it('restores the device and the facet layout under version 1 keys', () => {
    const storage = new Memory()
    storage.setItem(DEVICE_KEY, 'ZmFrZQ')
    storage.setItem(
      FACETS_KEY,
      JSON.stringify({ expanded: ['genre', 'nonsense'], collapsed: ['tag'] }),
    )
    const { selection, filters } = createAppStore(storage).getState()
    expect(selection.device).toBe('ZmFrZQ')
    expect([filters.expanded, filters.collapsed]).toEqual([['genre'], ['tag']])
  })

  it('writes the device and the facet layout when they change, and nothing else', () => {
    const storage = new Memory()
    const store = createAppStore(storage)
    store.getState().filters.setQuery('ignored')
    expect(storage.items.size).toBe(0)
    store.getState().selection.choose('dev')
    store.getState().filters.setUnfolded('region', true)
    expect(storage.getItem(DEVICE_KEY)).toBe('dev')
    expect(JSON.parse(storage.getItem(FACETS_KEY) ?? '')).toEqual({
      expanded: ['region'],
      collapsed: [],
    })
    store.getState().selection.choose(null)
    expect(storage.getItem(DEVICE_KEY)).toBe('')
  })

  it('works when storage is missing, refused or holds garbage', () => {
    const garbage = new Memory()
    garbage.setItem(FACETS_KEY, '{not json')
    for (const storage of [undefined, broken, garbage]) {
      const store = createAppStore(storage)
      store.getState().selection.choose('dev')
      store.getState().filters.setCollapsed('mode', true)
      expect(store.getState().selection.device).toBe('dev')
      expect(store.getState().filters.collapsed).toEqual(['mode'])
    }
  })
})
