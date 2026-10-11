/**
 * The search grammar (F11-S14), version 1's parseQuery and matchClause
 * ported exactly and pinned by the F0 grammar corpus.
 *
 * Bare words and quoted phrases must all appear in a game's haystack. A
 * `key op value` token is a clause: four numeric keys compare with > < >= <=
 * and equal with : or =; size compares the same way, but : or = means within
 * 5 per cent; the eight name keys match by containment.
 */
import { parseSize } from '../format/format'
import type { Game } from '../game/game'

export const KEYS = [
  'year',
  'size',
  'rating',
  'votes',
  'system',
  'genre',
  'region',
  'tag',
  'files',
  'franchise',
  'theme',
  'mode',
  'perspective',
] as const
export type Key = (typeof KEYS)[number]

export const COMPARATORS = ['>=', '<=', '>', '<', ':', '='] as const

export type NumericClause = {
  readonly key: 'year' | 'rating' | 'votes' | 'files'
  readonly op: '>' | '<' | '>=' | '<=' | '='
  readonly v: number
}
export type SizeClause = {
  readonly key: 'size'
  readonly op: '>' | '<' | '>=' | '<=' | '≈'
  readonly v: number | null
}
export type NameClause = {
  readonly key: Exclude<Key, NumericClause['key'] | 'size'>
  readonly op: '~'
  readonly v: string
}
export type Clause = NumericClause | SizeClause | NameClause

export type Query = { readonly terms: readonly string[]; readonly clauses: readonly Clause[] }

const OPS = new RegExp(`^(${KEYS.join('|')})\\s*(>=|<=|>|<|:|=)\\s*(.+)$`, 'i')
const NUMERIC: ReadonlySet<string> = new Set(['year', 'rating', 'votes', 'files'])

export function parseQuery(q: string): Query {
  const terms: string[] = []
  const clauses: Clause[] = []
  for (const m of q.matchAll(/"([^"]+)"|(\S+)/g)) {
    const token = m[1] || m[2] || ''
    const o = OPS.exec(token)
    if (!o) {
      terms.push(token.toLowerCase())
      continue
    }
    const key = (o[1] ?? '').toLowerCase() as Key
    const op = o[2] ?? ''
    const v = (o[3] ?? '').toLowerCase().replace(/^"|"$/g, '')
    const equal = op === ':' || op === '='
    if (NUMERIC.has(key))
      clauses.push({ key, op: equal ? '=' : op, v: parseFloat(v) } as NumericClause)
    else if (key === 'size')
      clauses.push({ key, op: equal ? '≈' : op, v: parseSize(v) } as SizeClause)
    else clauses.push({ key, op: '~', v } as NameClause)
  }
  return { terms, clauses }
}

function names(g: Game, key: NameClause['key']): readonly unknown[] {
  switch (key) {
    case 'system':
      return [g.system, g.sysLabel]
    case 'genre':
      return g.genres
    case 'region':
      return g.regions
    case 'tag':
      return g.tagNames
    default:
      return g.kinds[key]
  }
}

function numberOf(g: Game, key: NumericClause['key'] | 'size'): number | null {
  return key === 'files' ? g.files || 1 : g[key]
}

export function matchClause(g: Game, c: Clause): boolean {
  if (c.op === '~') return names(g, c.key).some((x) => String(x).toLowerCase().includes(c.v))
  const x = numberOf(g, c.key)
  if (x == null || c.v == null || Number.isNaN(c.v)) return false
  switch (c.op) {
    case '>':
      return x > c.v
    case '<':
      return x < c.v
    case '>=':
      return x >= c.v
    case '<=':
      return x <= c.v
    case '=':
      return x === c.v
    case '≈':
      return Math.abs(x - c.v) <= c.v * 0.05
  }
}

/** Every term is in the haystack and every clause holds. */
export function matchesQuery(g: Game, q: Query): boolean {
  return q.terms.every((t) => g.hay.includes(t)) && q.clauses.every((c) => matchClause(g, c))
}
