/**
 * The twin corpus: every synthetic game to version 1's exact and loose twin
 * keys, and to the twins version 1 lists for it, each marked loose or not.
 */
import { join } from 'node:path'
import { normalise } from '../fixture/fixture.ts'
import { syntheticLibrary } from '../library/library.ts'
import { UI_ROOT, bootV1 } from '../v1/v1.ts'

export const FIXTURE = join(UI_ROOT, 'src/lib/twins/__fixtures__/twins.v1.json')

export type TwinCase = {
  readonly id: number
  readonly title: string
  readonly igdb: string | null
  readonly system: string
  readonly exact: string
  readonly loose: string
  readonly twins: readonly { readonly id: number; readonly loose: boolean }[]
}

const READ = `S.games.map((g) => ({
  id: g.id, title: g.title, igdb: g.igdb, system: g.system,
  exact: twinKey(g), loose: twinKeyLoose(g),
  twins: twinsOf(g).map((t) => ({ id: t.g.id, loose: t.loose })),
}))`

export async function captureTwins(): Promise<TwinCase[]> {
  const v1 = await bootV1({ library: syntheticLibrary() })
  try {
    const cases = v1.evaluate<unknown>(READ)
    if (v1.errors.length) throw new Error(`version 1 reported: ${v1.errors.join('; ')}`)
    return normalise(cases) as TwinCase[]
  } finally {
    v1.close()
  }
}

export const TWINS = { name: 'twins', fixture: FIXTURE, capture: captureTwins } as const
