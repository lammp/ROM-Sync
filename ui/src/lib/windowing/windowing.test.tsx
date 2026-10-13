import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { GRID_GAP } from '../../design/tokens/tokens'
import { OVERSCAN, columns, rowHeight, template, useWindowedGrid, windowOf } from './windowing'

describe('the arithmetic', () => {
  it('fits columns with the token gap, at least one, one in a list', () => {
    expect(columns({ grid: true, width: 1000, pad: 0, tile: 150 })).toBe(
      Math.floor((1000 + GRID_GAP) / (150 + GRID_GAP)),
    )
    expect(columns({ grid: true, width: 10, pad: 0, tile: 150 })).toBe(1)
    expect(columns({ grid: true, width: 1000, pad: 0, tile: null })).toBe(6)
    expect(columns({ grid: false, width: 1000, pad: 0, tile: 150 })).toBe(1)
  })

  it('adds the gap below a grid row, not a list row', () => {
    expect([rowHeight(200, true), rowHeight(32, false)]).toEqual([200 + GRID_GAP, 32])
  })

  it('renders the rows in view and two either side', () => {
    const w = windowOf(1000, 5, 100, 1000, 300)
    expect([w.first, w.last]).toEqual([10 - OVERSCAN, 13 + OVERSCAN])
    expect([w.start, w.end, w.paddingTop, w.height]).toEqual([40, 75, 800, 20000])
  })

  it('writes a column template only for the grid', () => {
    expect([template(true, 3), template(false, 3)]).toEqual(['repeat(3, minmax(0, 1fr))', ''])
  })
})

/** jsdom lays nothing out, so the scroller's size and an item's height are given. */
const box = { width: 1000, height: 600, item: 200 }
const restore: (() => void)[] = []
function stub<T extends object>(proto: T, key: string, get: () => unknown) {
  const before = Object.getOwnPropertyDescriptor(proto, key)
  Object.defineProperty(proto, key, { configurable: true, get })
  restore.push(() =>
    before ? Object.defineProperty(proto, key, before) : Reflect.deleteProperty(proto, key),
  )
}

beforeEach(() => {
  stub(HTMLElement.prototype, 'clientWidth', () => box.width)
  stub(HTMLElement.prototype, 'clientHeight', () => box.height)
  const rect = Element.prototype.getBoundingClientRect
  Element.prototype.getBoundingClientRect = () => ({ height: box.item }) as DOMRect
  restore.push(() => (Element.prototype.getBoundingClientRect = rect))
})

afterEach(() => {
  while (restore.length) restore.pop()?.()
  vi.useRealTimers()
})

function Grid({ count }: { count: number }) {
  const { scroller, inner, layout: w } = useWindowedGrid(count, true, 150, count)
  return (
    <div ref={scroller} data-testid="scroller">
      <div ref={inner} style={{ height: w.height, paddingTop: w.paddingTop }}>
        {Array.from({ length: w.end - w.start }, (_, i) => (
          <div key={w.start + i}>item {w.start + i}</div>
        ))}
      </div>
    </div>
  )
}

describe('useWindowedGrid', () => {
  it('measures one row, then renders the window', () => {
    render(<Grid count={1000} />)
    expect(screen.getAllByText(/^item /)).toHaveLength(30)
    expect(screen.queryByText('item 30')).toBeNull()
  })

  it('moves the window when a scroll changes its rows', async () => {
    vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'cancelAnimationFrame'] })
    render(<Grid count={1000} />)
    const scroller = screen.getByTestId('scroller')
    scroller.scrollTop = 2000
    act(() => {
      scroller.dispatchEvent(new Event('scroll'))
      vi.advanceTimersToNextFrame()
    })
    expect(screen.queryByText('item 0')).toBeNull()
    expect(screen.getByText('item 42')).toBeTruthy()
    expect(screen.getAllByText(/^item /)).toHaveLength(48)
  })

  it('renders nothing for no items', () => {
    render(<Grid count={0} />)
    expect(screen.queryAllByText(/^item /)).toHaveLength(0)
  })

  it('stops listening when the page goes', () => {
    vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'cancelAnimationFrame'] })
    const { unmount } = render(<Grid count={1000} />)
    const scroller = screen.getByTestId('scroller')
    const removed = vi.spyOn(scroller, 'removeEventListener')
    scroller.dispatchEvent(new Event('scroll'))
    unmount()
    expect(removed).toHaveBeenCalledWith('scroll', expect.any(Function))
    expect(vi.getTimerCount()).toBe(0)
  })
})
