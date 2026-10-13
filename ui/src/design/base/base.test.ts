import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const css = readFileSync(join(import.meta.dirname, 'base.css'), 'utf8')

describe('base', () => {
  it('sets the page surface and body text from tokens', () => {
    expect(css).toMatch(/background: var\(--bg\);/)
    expect(css).toMatch(/color: var\(--fg\);/)
    expect(css).toMatch(/var\(--text-body\) \/ 1\.4/)
  })

  it('holds no colour literal of its own', () => {
    expect(css).not.toMatch(/#[0-9a-f]{3,8}\b|rgba?\(/i)
  })
})
