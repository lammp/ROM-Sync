import { describe, expect, it } from 'vitest'
import { SORTS, isSort, sortKey, sortTitle, sorted, type Sortable } from './sort'

const g = (key: string, over: Partial<Sortable> = {}): Sortable & { id: string } => ({
  id: key,
  sortKey: sortKey(key),
  sysKey: 'nes',
  year: null,
  rating: null,
  votes: null,
  size: 0,
  mtime: 0,
  ...over,
})

describe('sort keys', () => {
  it('drops a leading article, and only a leading one', () => {
    expect(sortTitle('The Legend of Zelda', 'x')).toBe('legend of zelda')
    expect(sortTitle('An American Tail', 'x')).toBe('american tail')
    expect(sortTitle('Theme Park', 'x')).toBe('theme park')
    expect(sortTitle('', 'File Name')).toBe('file name')
  })

  it('pads digit runs so 2 sorts before 10, and strips accents', () => {
    expect(sortKey('mega man 2') < sortKey('mega man 10')).toBe(true)
    expect(sortKey('pokémon')).toBe('pokemon')
  })
})

describe('sorted', () => {
  it('has six orders and falls back to title', () => {
    expect(SORTS).toHaveLength(6)
    expect(isSort('added')).toBe(false)
    expect(sorted([g('b'), g('a')], 'added').map((x) => x.id)).toEqual(['a', 'b'])
  })

  it('puts the newest, best, biggest and latest first, ties by title', () => {
    const list = [
      g('b', { year: 1990, rating: 80, votes: 5, size: 1, mtime: 2 }),
      g('a', { year: 1990, rating: 80, votes: 9, size: 9, mtime: 1 }),
      g('c', { year: 1999 }),
    ]
    expect(sorted(list, 'year').map((x) => x.id)).toEqual(['c', 'a', 'b'])
    expect(sorted(list, 'rating').map((x) => x.id)).toEqual(['a', 'b', 'c'])
    expect(sorted(list, 'size').map((x) => x.id)).toEqual(['a', 'b', 'c'])
    expect(sorted(list, 'mtime').map((x) => x.id)).toEqual(['b', 'a', 'c'])
  })

  it('orders systems by label, then title', () => {
    const list = [
      g('z', { sysKey: 'game boy' }),
      g('a', { sysKey: 'wii' }),
      g('b', { sysKey: 'game boy' }),
    ]
    expect(sorted(list, 'system').map((x) => x.id)).toEqual(['b', 'z', 'a'])
  })

  it('leaves the input alone', () => {
    const list = [g('b'), g('a')]
    sorted(list, 'title')
    expect(list.map((x) => x.id)).toEqual(['b', 'a'])
  })
})
