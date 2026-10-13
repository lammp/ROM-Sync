import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { check, layerOf, readTree, resolveImport } from './layering'

const SRC = join(import.meta.dirname, '../../src')

describe('layering', () => {
  it('the tree obeys the separation of duties', () => {
    expect(check(readTree(SRC))).toEqual([])
  })

  it('reads the tree it checks', () => {
    const files = Object.keys(readTree(SRC))
    expect(files).toContain('design/tokens/tokens.ts')
    expect(files).toContain('app/layout.tsx')
  })

  describe('each of six planted violations fails', () => {
    const rules = (sources: Record<string, string>) => check(sources).map((v) => v.rule)

    it('a component reads the store', () => {
      expect(
        rules({
          'components/atoms/Bad/Bad.tsx': "import { useStore } from '../../../store/store'",
        }),
      ).toEqual(['layer'])
    })

    it('a component calls a query or the generated client', () => {
      expect(
        rules({
          'components/molecules/Bad/Bad.tsx': "import { useJob } from '../../../queries/jobs/jobs'",
          'components/organisms/Bad/Bad.tsx': "import { client } from '../../../lib/api/client'",
        }),
      ).toEqual(['layer', 'layer'])
    })

    it('an atom imports upward', () => {
      expect(
        rules({ 'components/atoms/Bad/Bad.tsx': "import { Row } from '../../molecules/Row/Row'" }),
      ).toEqual(['layer'])
    })

    it('a feature imports another feature', () => {
      expect(
        rules({
          'features/devices/DevicesView/DevicesView.tsx':
            "import { LibraryView } from '../../library/LibraryView/LibraryView'",
        }),
      ).toEqual(['cross-feature'])
    })

    it('a module outside the store holds mutable state', () => {
      expect(rules({ 'lib/format/format.ts': 'let cache = 0\nexport const x = cache' })).toEqual([
        'module-state',
      ])
    })

    it('a colour literal outside tokens.ts', () => {
      expect(
        rules({
          'components/atoms/Bad/Bad.module.css': '.bad { color: #ff0000; }',
          'components/atoms/Worse/Worse.tsx': "const s = { color: 'rgba(0, 0, 0, 0.5)' }",
        }),
      ).toEqual(['colour-literal', 'colour-literal'])
    })
  })

  it('keeps the global stylesheets to the root layout', () => {
    expect(check({ 'app/layout.tsx': "import '../design/tokens/tokens.css'" })).toEqual([])
    expect(
      check({ 'app/devices/page.tsx': "import '../../design/base/base.css'" }).map((v) => v.rule),
    ).toEqual(['global-stylesheet'])
  })

  it('lets each layer import what section 14.3 allows', () => {
    expect(
      check({
        'components/organisms/Grid/Grid.tsx':
          "import { Tile } from '../../molecules/Tile/Tile'\nimport { Button } from '../../atoms/Button/Button'\nimport { sortKey } from '../../../lib/sort/sort'",
        'features/library/LibraryView/LibraryView.tsx':
          "import { Grid } from '../../../components/organisms/Grid/Grid'\nimport { useStore } from '../../../store/store'",
        'app/page.tsx': "import { LibraryView } from '../features/library/LibraryView/LibraryView'",
        'components/templates/Shell/Shell.tsx': "import type { ReactNode } from 'react'",
      }),
    ).toEqual([])
  })

  it('refuses what templates and routes may not import', () => {
    expect(
      check({
        'components/templates/Shell/Shell.tsx': "import { Tile } from '../../molecules/Tile/Tile'",
        'app/page.tsx': "import { Grid } from '../components/organisms/Grid/Grid'",
      }).map((v) => v.detail),
    ).toEqual([
      'templates imports molecules (components/molecules/Tile/Tile)',
      'app imports organisms (components/organisms/Grid/Grid)',
    ])
  })

  it('lets the store hold state, and tests and stories hold fixtures', () => {
    expect(
      check({
        'store/store.ts': 'let listeners = 0',
        'lib/sort/sort.test.ts': 'let seen = 0',
        'components/atoms/A/A.stories.tsx': 'let n = 0',
      }),
    ).toEqual([])
  })

  it('lets only the palette tests name a colour', () => {
    expect(check({ 'design/contrast/contrast.test.ts': "ratio('#ffffff', '#000000')" })).toEqual([])
    expect(
      check({ 'components/atoms/A/A.test.tsx': "expect(c).toBe('#ffffff')" }).map((v) => v.rule),
    ).toEqual(['colour-literal'])
  })

  it('reads no colour in a comment', () => {
    expect(
      check({ 'lib/x/x.ts': '// the old #2e323c line\n/* rgba(0,0,0,.5) */\nexport const x = 1' }),
    ).toEqual([])
  })

  it('classifies paths and resolves relative imports', () => {
    expect(layerOf('components/atoms/Button/Button.tsx')).toBe('atoms')
    expect(layerOf('lib/api/client.ts')).toBe('lib/api')
    expect(layerOf('components/unknown/X.tsx')).toBeUndefined()
    expect(layerOf('elsewhere/x.ts')).toBeUndefined()
    expect(resolveImport('app/page.tsx', 'react')).toBeUndefined()
    expect(resolveImport('app/devices/page.tsx', '../../store/store')).toBe('store/store')
  })
})
