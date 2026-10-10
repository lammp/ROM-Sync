import { describe, expect, test } from 'vitest'
import { readFixture } from '../fixture/fixture.ts'
import { v1Source } from '../v1/v1.ts'
import { FIXTURE, QUERIES, captureSearch, type SearchCase } from './search.capture.ts'

const COMPARATORS = ['>=', '<=', '>', '<', ':', '='] as const

function operatorKeys(): string[] {
  const match = /const OPS = \/\^\(([a-z|]+)\)/.exec(v1Source('app.js'))
  if (!match?.[1]) throw new Error('OPS not found in version 1')
  return match[1].split('|')
}

describe('search capture', () => {
  test('grammar_corpus', async () => {
    const { header, cases } = readFixture(FIXTURE)
    expect(header.corpus).toBe('search')
    expect(cases).toEqual(await captureSearch())
  })

  test('covers_every_operator_key', () => {
    const cases = readFixture(FIXTURE).cases as SearchCase[]
    const used = new Set(
      cases.flatMap((c) => (c.parsed as { clauses: { key: string }[] }).clauses.map((k) => k.key)),
    )
    const keys = operatorKeys()
    expect(keys).toHaveLength(13)
    for (const key of keys) expect(used, key).toContain(key)
  })

  test('covers_every_comparator', () => {
    const used = new Set<string>()
    for (const q of QUERIES) {
      for (const token of q.replace(/"/g, ' ').split(/\s+/)) {
        const m = /^[a-z]+(>=|<=|>|<|:|=)/i.exec(token)
        if (m?.[1]) used.add(m[1])
      }
    }
    for (const op of COMPARATORS) expect(used, op).toContain(op)
  })
})
