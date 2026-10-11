/**
 * A game as the library lists it, with what version 1's prep() derived from
 * it once so search, facets and sort never recompute it: the system's label,
 * the decade, the regions, the tags by kind, the haystack search reads and
 * the keys the library is sorted by.
 *
 * The input is structural: the engine's GameSummary fits it, and so does any
 * fixture, without this module importing the generated client.
 */
import { sortKey, sortTitle } from '../sort/sort'

export const TAG_KINDS = ['franchise', 'theme', 'mode', 'perspective'] as const
export type TagKind = (typeof TAG_KINDS)[number]

export type GameInput = {
  readonly id: number
  readonly name: string
  readonly title: string
  readonly igdb_name: string | null
  readonly system: string
  readonly genres: readonly string[]
  /** Accepted tags by kind, as the engine groups them. */
  readonly tags: Readonly<Record<string, readonly string[]>>
  readonly region: string | null
  readonly year: number | null
  readonly size: number
  readonly rating: number | null
  readonly votes: number | null
  readonly files: number
  readonly kind: string
  readonly matched: boolean
  readonly mtime: number
}

export type Game = GameInput & {
  readonly sysLabel: string
  readonly decade: string | null
  readonly regions: readonly string[]
  readonly tagNames: readonly string[]
  readonly kinds: Readonly<Record<TagKind | 'other', readonly string[]>>
  readonly otherTags: readonly string[]
  /** Everything a bare search term is looked for in, lower-cased, joined by " | ". */
  readonly hay: string
  readonly sortTitle: string
  readonly sortKey: string
  /** The system's label, lower-cased, for the system order. */
  readonly sysKey: string
}

export function prepare(g: GameInput, systems: Readonly<Record<string, string>>): Game {
  const sysLabel = systems[g.system] || g.system
  const regions = (g.region || '')
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)
  const kinds: Record<TagKind | 'other', string[]> = {
    franchise: [],
    theme: [],
    mode: [],
    perspective: [],
    other: [],
  }
  const tagNames: string[] = []
  for (const [kind, names] of Object.entries(g.tags)) {
    const bucket = (TAG_KINDS as readonly string[]).includes(kind)
      ? kinds[kind as TagKind]
      : kinds.other
    bucket.push(...names)
    tagNames.push(...names)
  }
  const hay = [
    g.title,
    g.name,
    g.igdb_name,
    sysLabel,
    g.system,
    ...g.genres,
    ...tagNames,
    ...regions,
  ]
    .filter(Boolean)
    .join(' | ')
    .toLowerCase()
  const title = sortTitle(g.title, g.name)
  return {
    ...g,
    sysLabel,
    decade: g.year ? `${Math.floor(g.year / 10) * 10}s` : null,
    regions,
    tagNames,
    kinds,
    otherTags: kinds.other,
    hay,
    sortTitle: title,
    sortKey: sortKey(title),
    sysKey: sysLabel.toLowerCase(),
  }
}
