/**
 * Fixtures: a header naming exactly which version 1 produced the cases, and
 * the cases themselves in JSON, with the few numbers JSON cannot hold marked.
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { V1_DIR, V1_TAG, v1Commit } from '../v1/v1.ts'

export type Header = {
  readonly tag: string
  readonly commit: string
  readonly source: string
  readonly corpus: string
  readonly locale: string
}

export type Fixture = { readonly header: Header; readonly cases: unknown }

const MARK = '$'
const SPECIAL: Record<string, unknown> = {
  NaN: NaN,
  Infinity: Infinity,
  '-Infinity': -Infinity,
  '-0': -0,
  undefined: undefined,
}

export function encode(value: unknown): unknown {
  if (typeof value === 'number') {
    if (Number.isNaN(value)) return { [MARK]: 'NaN' }
    if (value === Infinity) return { [MARK]: 'Infinity' }
    if (value === -Infinity) return { [MARK]: '-Infinity' }
    if (Object.is(value, -0)) return { [MARK]: '-0' }
    return value
  }
  if (value === undefined) return { [MARK]: 'undefined' }
  if (value === null || typeof value !== 'object') return value
  if (Array.isArray(value)) return value.map(encode)
  const kind = Object.prototype.toString.call(value)
  if (kind !== '[object Object]') throw new TypeError(`a fixture cannot hold ${kind}`)
  return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, encode(v)]))
}

export function decode(value: unknown): unknown {
  if (value === null || typeof value !== 'object') return value
  if (Array.isArray(value)) return value.map(decode)
  const entries = Object.entries(value)
  const only = entries[0]
  if (
    entries.length === 1 &&
    only &&
    only[0] === MARK &&
    typeof only[1] === 'string' &&
    only[1] in SPECIAL
  ) {
    return SPECIAL[only[1]]
  }
  return Object.fromEntries(entries.map(([k, v]) => [k, decode(v)]))
}

/** A value as it reads back from a fixture: plain, in this realm, special numbers kept. */
export function normalise(value: unknown): unknown {
  return decode(JSON.parse(JSON.stringify(encode(value))))
}
export function makeHeader(corpus: string): Header {
  return {
    tag: V1_TAG,
    commit: v1Commit(),
    source: `${V1_DIR}/app.js`,
    corpus,
    locale: Intl.DateTimeFormat().resolvedOptions().locale,
  }
}

export function writeFixture(path: string, corpus: string, cases: unknown): void {
  mkdirSync(dirname(path), { recursive: true })
  const fixture = { header: makeHeader(corpus), cases: encode(cases) }
  writeFileSync(path, JSON.stringify(fixture, null, 2) + '\n', 'utf8')
}

export function readFixture(path: string): Fixture {
  const raw = JSON.parse(readFileSync(path, 'utf8')) as { header: Header; cases: unknown }
  return { header: raw.header, cases: decode(raw.cases) }
}
