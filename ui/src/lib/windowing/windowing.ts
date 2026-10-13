/**
 * The windowed grid (F11-S17, D23): version 1's algorithm, ported, as a hook.
 *
 * Measure one row at the current width, then lay out for real: the spacer is
 * as tall as every row, its top padding skips the rows above the window, and
 * only the rows in view plus two either side are rendered. A scroll that
 * keeps the same rows in the window renders nothing. The gap is the token's
 * GRID_GAP, the one definition the stylesheet also reads.
 */
import { useCallback, useEffect, useLayoutEffect, useState } from 'react'
import { GRID_GAP, TILE } from '../../design/tokens/tokens'

/** Rows rendered beyond each edge of the viewport. */
export const OVERSCAN = 2

export type Measure = {
  readonly grid: boolean
  /** The scroller's client width, padding included. */
  readonly width: number
  /** Its horizontal padding on each side. */
  readonly pad: number
  /** The tile width in pixels; unset or zero falls back to 150. */
  readonly tile: number | null
}

/** Columns that fit: one in the list, at least one in the grid. */
export function columns(m: Measure, gap: number = GRID_GAP): number {
  if (!m.grid) return 1
  const tile = m.tile || TILE
  return Math.max(1, Math.floor((m.width - 2 * m.pad + gap) / (tile + gap)))
}

/** A measured item's height plus the gap below it in the grid. */
export function rowHeight(itemHeight: number, grid: boolean, gap: number = GRID_GAP): number {
  return itemHeight + (grid ? gap : 0)
}

export type Window = {
  readonly cols: number
  readonly rowH: number
  /** First and last rendered row; -1 and -1 when there is nothing. */
  readonly first: number
  readonly last: number
  /** The spacer's height and top padding, in pixels. */
  readonly height: number
  readonly paddingTop: number
  /** The items rendered: from `start` up to, not including, `end`. */
  readonly start: number
  readonly end: number
}

export const EMPTY_WINDOW = (cols: number): Window => ({
  cols,
  rowH: 0,
  first: -1,
  last: -1,
  height: 0,
  paddingTop: 0,
  start: 0,
  end: 0,
})

/** The rows in view, two either side, over `count` items in `cols` columns. */
export function windowOf(
  count: number,
  cols: number,
  rowH: number,
  scrollTop: number,
  viewport: number,
): Window {
  if (count === 0) return EMPTY_WINDOW(cols)
  const rows = Math.ceil(count / cols)
  const first = Math.max(0, Math.floor(scrollTop / rowH) - OVERSCAN)
  const last = Math.min(rows, Math.ceil((scrollTop + viewport) / rowH) + OVERSCAN)
  const start = first * cols
  const end = Math.max(start, Math.min(count, last * cols))
  return { cols, rowH, first, last, height: rows * rowH, paddingTop: first * rowH, start, end }
}

/** The grid template version 1 wrote: equal columns in the grid, none in the list. */
export function template(grid: boolean, cols: number): string {
  return grid ? `repeat(${cols}, minmax(0, 1fr))` : ''
}

export type WindowedGrid = {
  /** Callback ref for the scrolling element. */
  readonly scroller: (el: HTMLElement | null) => void
  /** Callback ref for the element holding the items; its first child is measured. */
  readonly inner: (el: HTMLElement | null) => void
  readonly layout: Window & {
    /** True while one row is rendered only to be measured. */
    readonly measuring: boolean
    readonly template: string
  }
}

type Seen = {
  readonly width: number
  readonly pad: number
  readonly viewport: number
  readonly scrollTop: number
}

function read(el: HTMLElement): Seen {
  const style = getComputedStyle(el)
  return {
    width: el.clientWidth,
    pad: (parseFloat(style.paddingLeft) + parseFloat(style.paddingRight)) / 2 || 0,
    viewport: el.clientHeight,
    scrollTop: el.scrollTop,
  }
}

type Measured = { readonly rowH: number; readonly basis: readonly unknown[] }

const same = (a: readonly unknown[], b: readonly unknown[]) =>
  a.length === b.length && a.every((x, i) => Object.is(x, b[i]))

/**
 * Windows `count` items into the scroller. `layoutKey` changes whenever the
 * items or their look change (filter, sort, view, tile size), which drops
 * the measurement as version 1's renderGrid did; so does a change of
 * columns.
 */
export function useWindowedGrid(
  count: number,
  grid: boolean,
  tile: number | null,
  layoutKey: unknown,
): WindowedGrid {
  const [scrollerEl, setScroller] = useState<HTMLElement | null>(null)
  const [innerEl, setInner] = useState<HTMLElement | null>(null)
  const [seen, setSeen] = useState<Seen>({ width: 0, pad: 0, viewport: 0, scrollTop: 0 })
  const cols = columns({ grid, width: seen.width, pad: seen.pad, tile })
  const basis = [layoutKey, grid, cols, tile]
  const [measured, setMeasured] = useState<Measured>({ rowH: 0, basis: [] })
  const rowH = same(measured.basis, basis) ? measured.rowH : 0

  // Measure one row at the current width, then lay out for real (D23). Setting
  // state from a layout effect is how a measurement reaches the next paint.
  useLayoutEffect(() => {
    if (rowH !== 0 || count === 0 || !innerEl) return
    const first = innerEl.firstElementChild
    const height = rowHeight(first ? first.getBoundingClientRect().height : 200, grid)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMeasured({ rowH: height, basis: [layoutKey, grid, cols, tile] })
  }, [rowH, count, innerEl, grid, cols, tile, layoutKey])

  // Scrolls are read once a frame, and only a change of rows re-renders.
  useEffect(() => {
    if (!scrollerEl || rowH === 0) return
    let frame = 0
    const onScroll = () => {
      if (frame) return
      frame = requestAnimationFrame(() => {
        frame = 0
        const next = read(scrollerEl)
        setSeen((prev) => {
          const was = windowOf(count, cols, rowH, prev.scrollTop, prev.viewport)
          const now = windowOf(count, cols, rowH, next.scrollTop, next.viewport)
          return was.first === now.first && was.last === now.last ? prev : next
        })
      })
    }
    scrollerEl.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      scrollerEl.removeEventListener('scroll', onScroll)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [scrollerEl, count, cols, rowH])

  // A resize settles for 80 ms, then the row is measured again.
  useEffect(() => {
    if (!scrollerEl || typeof ResizeObserver === 'undefined') return
    let timer: ReturnType<typeof setTimeout> | undefined
    const observer = new ResizeObserver(() => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        setSeen(read(scrollerEl))
        setMeasured({ rowH: 0, basis: [] })
      }, 80)
    })
    observer.observe(scrollerEl)
    return () => {
      observer.disconnect()
      clearTimeout(timer)
    }
  }, [scrollerEl])

  const scroller = useCallback((el: HTMLElement | null) => {
    setScroller(el)
    if (el) setSeen(read(el))
  }, [])
  const inner = useCallback((el: HTMLElement | null) => setInner(el), [])

  const measuring = rowH === 0 && count > 0
  const win =
    rowH === 0 ? EMPTY_WINDOW(cols) : windowOf(count, cols, rowH, seen.scrollTop, seen.viewport)
  return {
    scroller,
    inner,
    layout: {
      ...(measuring ? { ...win, start: 0, end: Math.min(count, cols) } : win),
      measuring,
      template: template(grid, cols),
    },
  }
}
