/**
 * The windowing corpus: grid width, padding, tile size, measured tile height,
 * viewport, scroll position and list length to version 1's column count, row
 * height, row window, spacer sizes and rendered tile count.
 *
 * The browser's measurements are inputs here, supplied by replacing what
 * version 1 asks the layout engine for. Measuring them in a real browser is
 * F11-S26's story, in Chromium.
 */
import { join } from 'node:path'
import { normalise } from '../fixture/fixture.ts'
import { syntheticLibrary } from '../library/library.ts'
import { UI_ROOT, bootV1 } from '../v1/v1.ts'

export const FIXTURE = join(UI_ROOT, 'src/lib/windowing/__fixtures__/windowing.v1.json')

export type Layout = {
  readonly name: string
  readonly grid: boolean
  readonly width: number
  readonly pad: number
  readonly tile: number | null
  readonly tileHeight: number
  readonly height: number
  readonly scroll: number
  readonly n: number
  readonly scrollTo?: number
}

const base = {
  grid: true,
  width: 1000,
  pad: 0,
  tile: 150,
  tileHeight: 200,
  height: 600,
  scroll: 0,
  n: 74,
}

export const LAYOUTS: readonly Layout[] = [
  ...[0, 149, 150, 163, 164, 314, 328, 1000, 1920].map((width) => ({
    ...base,
    name: `width ${width}`,
    width,
  })),
  { ...base, name: 'tile 100', tile: 100 },
  { ...base, name: 'tile 200', tile: 200 },
  { ...base, name: 'tile unset falls back to 150', tile: null },
  { ...base, name: 'padding 16 at 328', width: 328, pad: 16 },
  { ...base, name: 'no games', n: 0 },
  { ...base, name: 'one game', n: 1 },
  { ...base, name: 'five games', n: 5 },
  { ...base, name: 'a thousand games', n: 1000 },
  { ...base, name: 'scrolled 500', n: 1000, scroll: 500 },
  { ...base, name: 'scrolled to the end', n: 1000, scroll: 50000 },
  { ...base, name: 'no viewport', height: 0 },
  { ...base, name: 'taller tiles', tileHeight: 236, n: 1000, scroll: 1000 },
  { ...base, name: 'a small scroll keeps the window', n: 1000, scrollTo: 40 },
  { ...base, name: 'a long scroll moves the window', n: 1000, scrollTo: 2000 },
  { ...base, name: 'list', grid: false, tileHeight: 32, n: 1000 },
  {
    ...base,
    name: 'list scrolled',
    grid: false,
    tileHeight: 32,
    n: 1000,
    scroll: 3200,
    scrollTo: 6400,
  },
]

const READ = `(function (c) {
  const grid = document.querySelector('#grid');
  Object.defineProperty(grid, 'clientWidth', { configurable: true, get: () => c.width });
  Object.defineProperty(grid, 'clientHeight', { configurable: true, get: () => c.height });
  Object.defineProperty(grid, 'scrollTop', { configurable: true, get: () => c.scroll, set: () => {} });
  const root = document.documentElement;
  globalThis.getComputedStyle = (el) =>
    el === grid ? { paddingLeft: c.pad + 'px', paddingRight: c.pad + 'px' }
    : el === root ? { getPropertyValue: (p) => (p === '--tile' && c.tile != null ? c.tile + 'px' : '') }
    : { getPropertyValue: () => '' };
  Element.prototype.getBoundingClientRect = function () { return { height: c.tileHeight, width: 0, top: 0, left: 0, right: 0, bottom: 0 }; };
  const read = () => {
    const inner = document.querySelector('#grid-inner');
    return {
      cols: V.cols, rowH: V.rowH, first: V.first, last: V.last,
      height: inner.style.height, paddingTop: inner.style.paddingTop, template: inner.style.gridTemplateColumns,
      rendered: inner.querySelectorAll('[data-id]').length, empty: inner.textContent === 'nothing matches',
    };
  };
  S.grid = c.grid;
  S.filtered = Array.from({ length: c.n }, (_, i) => S.games[i % S.games.length]);
  V.rowH = 0;
  renderGrid();
  const first = read();
  let after = null;
  if (c.scrollTo != null) {
    const before = document.querySelector('#grid-inner').innerHTML;
    c.scroll = c.scrollTo;
    renderWindow(false);
    after = { ...read(), redrawn: document.querySelector('#grid-inner').innerHTML !== before };
  }
  return { first, after };
})`

export type WindowCase = {
  readonly layout: Layout
  readonly first: object
  readonly after: object | null
}

export async function captureWindowing(): Promise<WindowCase[]> {
  const v1 = await bootV1({ library: syntheticLibrary() })
  try {
    const cases = LAYOUTS.map((layout) => ({
      layout,
      ...v1.evaluate<object>(`${READ}(${JSON.stringify(layout)})`),
    }))
    if (v1.errors.length) throw new Error(`version 1 reported: ${v1.errors.join('; ')}`)
    return normalise(cases) as WindowCase[]
  } finally {
    v1.close()
  }
}

export const WINDOWING = { name: 'windowing', fixture: FIXTURE, capture: captureWindowing } as const
