/**
 * F11-S12: anything that moves stops when the reader asks for reduced motion.
 * Every stylesheet that declares an animation or a transition also declares,
 * in a prefers-reduced-motion block, a rule that turns each of them off.
 */
import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC = join(import.meta.dirname, '../../src')
const REDUCED = /@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{([\s\S]*?\})\s*\}/g
const RULE = /([^{}]+)\{([^{}]*)\}/g

function sheets(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory()
      ? sheets(join(dir, e.name))
      : e.name.endsWith('.css')
        ? [join(dir, e.name)]
        : [],
  )
}

/** Selectors whose rules move, and the selectors a reduced-motion block stills. */
export function motion(css: string): { moving: string[]; stilled: string[] } {
  const reduced = [...css.matchAll(REDUCED)].map((m) => m[1] ?? '')
  const outside = css
    .replace(REDUCED, '')
    .replace(/@keyframes[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}/g, '')
  const moving = [...outside.matchAll(RULE)]
    .filter(([, , body]) => /(^|;|\s)(animation|transition)\s*:/.test(body ?? ''))
    .map(([, selector]) => (selector ?? '').trim())
  const stilled = reduced.flatMap((block) =>
    [...block.matchAll(RULE)]
      .filter(([, , body]) => /(animation|transition)\s*:\s*none/.test(body ?? ''))
      .map(([, selector]) => (selector ?? '').trim()),
  )
  return { moving, stilled }
}

describe('motion', () => {
  it('respects_preference', () => {
    const found: string[] = []
    for (const file of sheets(SRC)) {
      const { moving, stilled } = motion(readFileSync(file, 'utf8'))
      for (const selector of moving) {
        found.push(selector)
        expect(stilled, `${relative(SRC, file)}: ${selector}`).toContain(selector)
      }
    }
    expect(found).toEqual(expect.arrayContaining(['.spin', '.chev']))
  })

  it('catches motion with no reduced-motion rule', () => {
    expect(motion('.a { transition: width 0.3s; }')).toEqual({ moving: ['.a'], stilled: [] })
    expect(
      motion(
        '.a { animation: spin 1s; }\n@keyframes spin { to { transform: rotate(1turn); } }\n@media (prefers-reduced-motion: reduce) { .a { animation: none; } }',
      ),
    ).toEqual({ moving: ['.a'], stilled: ['.a'] })
  })
})
