/**
 * F11-S9: the focus ring. One rule in base.css draws it on every control: a
 * 2 px `--focus` outline set 2 px off the control, so the gap shows the
 * surrounding surface and the ring is measured against that surface rather
 * than the control's fill. No stylesheet may take it away.
 */
import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'
import { SURFACES, TARGET, ratio } from '../../src/design/contrast/contrast'
import { COLOUR } from '../../src/design/tokens/tokens'

const SRC = join(import.meta.dirname, '../../src')
const base = readFileSync(join(SRC, 'design/base/base.css'), 'utf8')

function sheets(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory()
      ? sheets(join(dir, e.name))
      : e.name.endsWith('.css')
        ? [join(dir, e.name)]
        : [],
  )
}

describe('focus', () => {
  it('draws a 2 px --focus ring 2 px off every focused control', () => {
    const rule = /:focus-visible\s*\{([^}]*)\}/.exec(base)?.[1] ?? ''
    expect(rule).toMatch(/outline:\s*2px solid var\(--focus\);/)
    expect(rule).toMatch(/outline-offset:\s*2px;/)
  })

  it('visible_on_every_surface', () => {
    for (const surface of SURFACES)
      expect(ratio(COLOUR['--focus'], COLOUR[surface]), surface).toBeGreaterThanOrEqual(
        TARGET['non-text'],
      )
  })

  it('is never taken away', () => {
    for (const file of sheets(SRC)) {
      const css = readFileSync(file, 'utf8')
      expect(css, relative(SRC, file)).not.toMatch(/outline:\s*(none|0)\b/)
      expect(css, relative(SRC, file)).not.toMatch(/:focus(-visible)?\s*\{[^}]*outline-color/)
    }
  })
})
