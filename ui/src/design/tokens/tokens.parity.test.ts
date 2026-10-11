/**
 * Version 1's palette, held: every declared token keeps its value, every
 * passing pair is drawn from the token set, and every failing pair is
 * replaced by the correction CAPTURE-TOKENS section 5 declares.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { COLOUR, TOKENS, type ColourToken } from './tokens'

type Pair = { label: string; fg: string; bg: string; verdict: 'PASS' | 'FAIL' }
const fixture = JSON.parse(
  readFileSync(join(import.meta.dirname, '__fixtures__/palette.v1.json'), 'utf8'),
) as { cases: { tokens: Record<string, string>; pairs: Pair[] } }
const { tokens, pairs } = fixture.cases

/** `--line` did two jobs and is split; the decorative half keeps its value. */
const RENAMED: Record<string, ColourToken> = { '--line': '--divider' }

/** Near-duplicates of a token, collapsed into it (CAPTURE-TOKENS section 3). */
const COLLAPSED: Record<string, ColourToken> = {
  '#9aa3ad': '--muted',
  '#8b939d': '--muted',
  '#e6e9ee': '--fg',
}

/** Each failing pair, and the token that replaces its failing side. */
const CORRECTED: Record<string, ColourToken> = {
  'primary button label': '--accent-solid',
  'segmented active label': '--accent-solid',
  'system file active row label': '--accent-solid',
  'selection tick glyph': '--on-ok',
  'control border on page': '--border',
  'control border on panel': '--border',
  'control border on raised': '--border',
  'meter track on panel': '--border',
  'lamp off on panel': '--lamp-off',
}

const VALUES = new Set<string>(Object.values(COLOUR))
const known = (hex: string) => VALUES.has(hex) || hex in COLLAPSED

describe('palette parity', () => {
  it('keeps every declared version 1 token', () => {
    for (const [name, value] of Object.entries(tokens)) {
      const now = RENAMED[name] ?? name
      expect(TOKENS[now as keyof typeof TOKENS], name).toBe(value)
    }
  })

  it('draws every passing pair from the token set', () => {
    for (const p of pairs.filter((p) => p.verdict === 'PASS')) {
      expect(known(p.fg) && known(p.bg), p.label).toBe(true)
    }
  })

  it('replaces every failing pair with its declared correction', () => {
    const failing = pairs.filter((p) => p.verdict === 'FAIL')
    expect(failing.map((p) => p.label).sort()).toEqual(Object.keys(CORRECTED).sort())
    for (const p of failing) {
      const token = CORRECTED[p.label] as ColourToken
      expect([p.fg, p.bg], p.label).not.toContain(COLOUR[token])
    }
  })

  it('collapses only into tokens that exist', () => {
    for (const token of Object.values(COLLAPSED)) expect(COLOUR[token]).toBeDefined()
  })
})
