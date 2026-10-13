/**
 * The format corpus: bytes to strings, size strings to bytes, and seconds to
 * an estimate, through version 1's fmtB, parseSize and fmtEta, including the
 * negatives, nulls and non-numbers each one meets.
 */
import { join } from 'node:path'
import { normalise } from '../fixture/fixture.ts'
import { syntheticLibrary } from '../library/library.ts'
import { UI_ROOT, bootV1 } from '../v1/v1.ts'

export const FIXTURE = join(UI_ROOT, 'src/lib/format/__fixtures__/format.v1.json')

export type FormatCases = {
  readonly fmtB: readonly { readonly in: unknown; readonly out: string }[]
  readonly parseSize: readonly { readonly in: unknown; readonly out: number | null }[]
  readonly fmtEta: readonly { readonly in: unknown; readonly out: string }[]
}

const READ = `(() => ({
  fmtB: [null, undefined, NaN, 0, 1, 0.5, 9.99, 1023, 1024, 1536, 10239, 10240, 102400, 1048575, 1048576, 5e9,
         1099511627776, 1125899906842624, -1, -2048, -1048576]
    .map((x) => ({ in: x, out: fmtB(x) })),
  parseSize: ['10mb', '10 MB', '2gb', '2 gb', '512k', '512 K', '1.5m', '.5g', '1t', '1tb', '100', '100b', '7kb  ',
              '  7kb', 'abc', '', '1e3', '10 m b', '1..2mb', '-5mb', '5 xb', 0, 1024, null]
    .map((x) => ({ in: x, out: parseSize(x) })),
  fmtEta: [null, undefined, NaN, Infinity, -Infinity, -5, 0, 0.2, 0.5, 1, 1.4, 59.4, 59.6, 60, 89, 90, 3599,
           3600, 5400, 86400]
    .map((x) => ({ in: x, out: fmtEta(x) })),
}))()`

export async function captureFormat(): Promise<FormatCases> {
  const v1 = await bootV1({ library: syntheticLibrary() })
  try {
    const cases = v1.evaluate<unknown>(READ)
    if (v1.errors.length) throw new Error(`version 1 reported: ${v1.errors.join('; ')}`)
    return normalise(cases) as FormatCases
  } finally {
    v1.close()
  }
}

export const FORMAT = { name: 'format', fixture: FIXTURE, capture: captureFormat } as const
