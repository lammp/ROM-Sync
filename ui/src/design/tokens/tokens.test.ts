import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { COLOUR, GRID_GAP, LAYOUT, RADIUS, TEXT, TILE, TOKENS, cssVar, stylesheet } from './tokens'

const CSS = join(import.meta.dirname, 'tokens.css')
const HEX = /^#[0-9a-f]{6}$/
const RGBA = /^rgba\(\d{1,3}, \d{1,3}, \d{1,3}, (0(\.\d+)?|1)\)$/
const LENGTH = /^(\d+px|\d+%|0)( (\d+px|0)){0,3}$/

describe('tokens', () => {
  it('generated_matches_source', () => {
    expect(readFileSync(CSS, 'utf8')).toBe(stylesheet())
  })

  it('declares every token once, in the order of its group', () => {
    const declared = [...stylesheet().matchAll(/^ {2}(--[a-z0-9-]+):/gm)].map((m) => m[1])
    expect(declared).toEqual(Object.keys(TOKENS))
    expect(new Set(declared).size).toBe(declared.length)
  })

  it('writes every colour as six-digit lower-case hex or a spaced rgba', () => {
    for (const [name, value] of Object.entries(COLOUR)) {
      expect(HEX.test(value) || RGBA.test(value), `${name}: ${value}`).toBe(true)
    }
  })

  it('writes every size, radius and layout value as a length', () => {
    for (const [name, value] of Object.entries({ ...TEXT, ...RADIUS, ...LAYOUT })) {
      expect(LENGTH.test(value), `${name}: ${value}`).toBe(true)
    }
  })

  it('has one definition of the grid geometry', () => {
    expect(LAYOUT['--tile']).toBe(`${TILE}px`)
    expect(LAYOUT['--grid-gap']).toBe(`${GRID_GAP}px`)
  })

  it('names a token as a var() reference', () => {
    expect(cssVar('--focus')).toBe('var(--focus)')
  })

  it('has no light theme, by decision', () => {
    expect(stylesheet()).not.toContain('prefers-color-scheme')
  })
})
