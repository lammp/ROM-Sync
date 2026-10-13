/**
 * F11-S25: no native dialog anywhere in the interface. Version 1 had five
 * confirm() calls and one prompt(); SPEC section 10 forbids them all, with
 * alert() for good measure.
 */
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { readTree } from '../layering/layering'

const SRC = join(import.meta.dirname, '../../src')
const NATIVE = /(?<![\w.])(?:window\.)?(confirm|prompt|alert)\s*\(/

export function nativeDialogs(sources: Record<string, string>): string[] {
  return Object.entries(sources)
    .filter(([file]) => !/\.(test|stories)\.tsx?$/.test(file))
    .flatMap(([file, source]) => {
      const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/.*$/gm, '$1')
      const hit = NATIVE.exec(code)
      return hit ? [`${file}: ${hit[0]}`] : []
    })
}

describe('no native dialogs', () => {
  it('none in the interface', () => {
    expect(nativeDialogs(readTree(SRC))).toEqual([])
  })

  it('catches each kind, and not a method of the same name', () => {
    expect(
      nativeDialogs({
        'a.ts': "if (confirm('sure?')) go()",
        'b.ts': "const n = window.prompt('name')",
        'c.ts': 'alert(1)',
        'd.ts': 'dialog.confirm(); onConfirm()',
        'e.ts': '// confirm() in a comment',
      }),
    ).toEqual(['a.ts: confirm(', 'b.ts: window.prompt(', 'c.ts: alert('])
  })
})
