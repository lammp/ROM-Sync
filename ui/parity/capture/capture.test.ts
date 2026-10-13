import { spawnSync } from 'node:child_process'
import { relative } from 'node:path'
import { describe, expect, test } from 'vitest'
import { findFixtures } from '../provenance/provenance.ts'
import { REPO_ROOT, UI_ROOT } from '../v1/v1.ts'
import { CORPORA, captureAll } from './capture.ts'

describe('capture', () => {
  test('corpus_names_are_unique', () => {
    const names = CORPORA.map((c) => c.name)
    expect(new Set(names).size).toBe(names.length)
  })

  test('every_fixture_sits_with_a_function', () => {
    for (const c of CORPORA) {
      expect(relative(UI_ROOT, c.fixture).replace(/\\/g, '/'), c.name).toMatch(
        /^src\/(lib|design)\/[a-z]+\/__fixtures__\/[a-z]+\.v1\.json$/,
      )
    }
  })

  test('every_fixture_is_registered', () => {
    const registered = new Set(CORPORA.map((c) => c.fixture))
    for (const path of findFixtures()) expect(registered, path).toContain(path)
    for (const c of CORPORA) expect(findFixtures(), c.name).toContain(c.fixture)
  })

  test('every_fixture_is_committable', () => {
    // a fixture the ignore rules hide is a fixture a clean clone does not have
    for (const c of CORPORA) {
      const ignored = spawnSync('git', ['check-ignore', '-q', c.fixture], { cwd: REPO_ROOT })
      expect(ignored.status, `${c.name}: ${c.fixture} is ignored by .gitignore`).toBe(1)
    }
  })

  test('refuses_an_unknown_corpus', async () => {
    await expect(captureAll(['nope'])).rejects.toThrow('no such corpus: nope')
  })
})
