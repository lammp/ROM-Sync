/**
 * The sort corpus: every synthetic title to version 1's sort title and sort
 * key, the library's order under each of the six sort modes, and the size
 * slider's log scale in both directions.
 */
import { join } from 'node:path'
import { normalise } from '../fixture/fixture.ts'
import { syntheticLibrary } from '../library/library.ts'
import { UI_ROOT, bootV1 } from '../v1/v1.ts'

export const FIXTURE = join(UI_ROOT, 'src/lib/sort/__fixtures__/sort.v1.json')

export type SortCases = {
  readonly keys: readonly {
    readonly id: number
    readonly title: string
    readonly sortTitle: string
    readonly sortKey: string
    readonly sysKey: string
  }[]
  readonly orders: Readonly<Record<string, readonly number[]>>
  readonly scale: {
    readonly sizeLog: { readonly min: number; readonly max: number }
    readonly toBytes: readonly { readonly slider: number; readonly bytes: number | null }[]
    readonly toSlider: readonly { readonly bytes: number | null; readonly slider: number | null }[]
  }
}

const READ = `(() => {
  const keys = S.games.map((g) => ({ id: g.id, title: g.title, sortTitle: g.sortTitle, sortKey: g.sortKey, sysKey: g.sysKey }));
  const orders = {};
  for (const mode of Object.keys(CMP).concat(['unknown-mode'])) {
    S.sort = mode; S.sortedBy = null;
    orders[mode] = sortedGames().map((g) => g.id);
  }
  S.sort = 'title'; S.sortedBy = null;
  const sliders = [-1, 0, 1, 10, 100, 250, 500, 750, 990, 999, 1000, 1200];
  const bytes = [null, 0, 1, 512, 1024, 4096, 1048576, 1073741824, 1e12];
  return {
    keys, orders,
    scale: {
      sizeLog: { min: S.sizeLog.min, max: S.sizeLog.max },
      toBytes: sliders.map((v) => ({ slider: v, bytes: sliderToBytes(v) })),
      toSlider: bytes.map((b) => ({ bytes: b, slider: bytesToSlider(b) })),
    },
  };
})()`

export async function captureSort(): Promise<SortCases> {
  const v1 = await bootV1({ library: syntheticLibrary() })
  try {
    const cases = v1.evaluate<unknown>(READ)
    if (v1.errors.length) throw new Error(`version 1 reported: ${v1.errors.join('; ')}`)
    return normalise(cases) as SortCases
  } finally {
    v1.close()
  }
}

export const SORT = { name: 'sort', fixture: FIXTURE, capture: captureSort } as const
