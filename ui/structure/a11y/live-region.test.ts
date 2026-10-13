/**
 * F11-S36, at the source: there is one way to show a transient message, and
 * it leads to the one live region. Every toast goes through the store's
 * `ui.toast`; only the shell's Toasts feature draws the Toast molecule; the
 * root layout mounts it once, so the region is in the page before any toast.
 * The end-to-end spec e2e/a11y/live-region.spec.ts shows it announcing.
 */
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { readTree } from '../layering/layering'

const SRC = join(import.meta.dirname, '..', '..', 'src')
const isCode = (f: string) => /\.tsx?$/.test(f) && !/\.(test|stories)\.tsx?$/.test(f)

export function strayAnnouncers(tree: Readonly<Record<string, string>>): string[] {
  const out: string[] = []
  for (const [file, source] of Object.entries(tree)) {
    if (!isCode(file)) continue
    if (/\b(window\.)?alert\(/.test(source)) out.push(`${file}: alert()`)
    if (/molecules\/Toast\/Toast'/.test(source) && file !== 'features/shell/Toasts/Toasts.tsx')
      out.push(`${file}: draws Toast itself`)
    if (/<Toasts\b/.test(source) && file !== 'app/layout.tsx') out.push(`${file}: mounts Toasts`)
  }
  const mounts = (tree['app/layout.tsx'] ?? '').match(/<Toasts\b/g)?.length ?? 0
  if (mounts !== 1) out.push(`app/layout.tsx: mounts Toasts ${mounts} times`)
  return out
}

describe('live region', () => {
  it('announces_every_toast: one way to a toast, and one region it lands in', () => {
    expect(strayAnnouncers(readTree(SRC))).toEqual([])
  })

  it('catches another way to announce', () => {
    expect(
      strayAnnouncers({
        'features/x/X/X.tsx':
          "import { Toast } from '../../../components/molecules/Toast/Toast'\nalert('hi')",
        'app/layout.tsx': '<Toasts /> <Toasts />',
      }),
    ).toEqual([
      'features/x/X/X.tsx: alert()',
      'features/x/X/X.tsx: draws Toast itself',
      'app/layout.tsx: mounts Toasts 2 times',
    ])
  })
})
