import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { check, readTree } from './companions'

const UI = join(import.meta.dirname, '../..')
const rules = (tree: Record<string, string>) => check(tree).map((m) => `${m.rule}: ${m.detail}`)

const COMPOSED =
  "import { composeStories } from '@storybook/react'\nimport * as stories from './Chip.stories'"

describe('companions', () => {
  it('every folder holds its companions', () => {
    expect(check(readTree(UI))).toEqual([])
  })

  it('reads the tree it checks', () => {
    const files = Object.keys(readTree(UI))
    expect(files).toContain('src/components/atoms/Button/Button.stories.tsx')
    expect(files).toContain('src/lib/format/__fixtures__/format.v1.json')
    expect(files.some((f) => f.includes('node_modules'))).toBe(false)
  })

  describe('each planted violation fails', () => {
    it('a component without its stories', () => {
      expect(
        rules({
          'src/components/atoms/Chip/Chip.tsx': '',
          'src/components/atoms/Chip/Chip.test.tsx': COMPOSED,
        }),
      ).toEqual(['component: Chip.stories.tsx'])
    })

    it('a component test that rebuilds its props', () => {
      expect(
        rules({
          'src/components/atoms/Chip/Chip.tsx': '',
          'src/components/atoms/Chip/Chip.stories.tsx': '',
          'src/components/atoms/Chip/Chip.test.tsx': "render(<Chip kind='system'>x</Chip>)",
        }),
      ).toEqual(['compose: Chip.test.tsx does not compose ./Chip.stories'])
    })

    it('a function without its test', () => {
      expect(rules({ 'src/lib/sort/sort.ts': '' })).toEqual(['function: sort.test.ts'])
    })

    it('a captured corpus without its parity test', () => {
      expect(
        rules({
          'src/lib/sort/sort.ts': '',
          'src/lib/sort/sort.test.ts': '',
          'src/lib/sort/__fixtures__/sort.v1.json': '{}',
        }),
      ).toEqual(['parity: sort.parity.test.ts'])
    })

    it('a barrel file', () => {
      expect(rules({ 'src/lib/index.ts': '' })).toEqual(['barrel: index.ts'])
    })

    it('an end-to-end spec outside its flow folder', () => {
      expect(rules({ 'e2e/library.spec.ts': '' })).toEqual([
        'e2e: library.spec.ts belongs in e2e/library/',
      ])
    })
  })

  it('lets a corpus wait for its function, and a folder of folders hold none', () => {
    expect(
      check({
        'src/lib/twins/__fixtures__/twins.v1.json': '{}',
        'src/store/slices/ui/ui.ts': '',
        'src/store/slices/ui/ui.test.ts': '',
        'e2e/library/library.spec.ts': '',
        'e2e/a11y/keyboard.spec.ts': '',
      }),
    ).toEqual([])
  })

  it('takes a .tsx source and test in a function folder', () => {
    expect(
      check({ 'src/queries/engine/engine.tsx': '', 'src/queries/engine/engine.test.tsx': '' }),
    ).toEqual([])
  })
})
