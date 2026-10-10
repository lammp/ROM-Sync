/**
 * The search corpus: query strings to version 1's parsed terms and clauses,
 * and to the games each query matches in the synthetic library.
 */
import { join } from 'node:path'
import { normalise } from '../fixture/fixture.ts'
import { syntheticLibrary } from '../library/library.ts'
import { UI_ROOT, bootV1 } from '../v1/v1.ts'

export const FIXTURE = join(UI_ROOT, 'src/lib/search/__fixtures__/grammar.v1.json')

export const QUERIES: readonly string[] = [
  '',
  '   ',
  'mario',
  'Mario Kart',
  '"mario kart"',
  'MARIO',
  'zelda year>1990',
  'year>1990',
  'year>=1991',
  'year<=1990',
  'year<1985',
  'year:1998',
  'year=1998',
  'YEAR>1990',
  'year>abc',
  'year:',
  'size>10mb',
  'size<1g',
  'size:512k',
  'size=2gb',
  'size>=1.5mb',
  'size<=100kb',
  'size:1t',
  'size:abc',
  'size:300',
  'rating>80',
  'rating>=90',
  'rating<60',
  'rating:66',
  'votes>100',
  'votes<10',
  'votes>=0',
  'files>1',
  'files:1',
  'files=3',
  'system:nes',
  'system:Nintendo',
  'system=snes',
  'system:snes system:nes',
  'genre:rpg',
  'genre:role-playing',
  'region:japan',
  'region=usa',
  '"tag:tag 01"',
  'tag:tag',
  'franchise:mario',
  'theme:fantasy',
  'mode:multiplayer',
  'perspective:side',
  'Perspective:eye',
  'year>1990 genre:platform mario',
  'year>1985 year<1990',
  '""',
  '"unclosed',
  'mega man 2',
  '"mega man 2"',
  'pokémon',
  'pokemon',
  'genre:',
  'notakey:value',
  'year >1990',
  'year> 1990',
]

export type SearchCase = { readonly q: string; readonly parsed: unknown; readonly matches: unknown }

export async function captureSearch(): Promise<SearchCase[]> {
  const v1 = await bootV1({ library: syntheticLibrary() })
  try {
    const cases = QUERIES.map((q) => {
      const literal = JSON.stringify(q)
      return {
        q,
        parsed: v1.evaluate<unknown>(`parseQuery(${literal})`),
        matches: v1.evaluate<unknown>(
          `S.games.filter((g) => passesQuery(g, parseQuery(${literal}))).map((g) => g.id)`,
        ),
      }
    })
    if (v1.errors.length) throw new Error(`version 1 reported: ${v1.errors.join('; ')}`)
    return normalise(cases) as SearchCase[]
  } finally {
    v1.close()
  }
}

export const SEARCH = { name: 'search', fixture: FIXTURE, capture: captureSearch } as const
