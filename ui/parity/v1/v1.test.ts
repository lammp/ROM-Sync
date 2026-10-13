import { describe, expect, test } from 'vitest'
import { bootV1, v1Commit, v1Source } from './v1.ts'

const library = {
  systems: { nes: 'Nintendo Entertainment System' },
  games: [
    {
      id: 1,
      name: 'Synthetic One',
      title: 'Super Mario Bros. 3',
      igdb: null,
      system: 'nes',
      genres: ['Platform'],
      tags: [],
      region: 'USA',
      year: 1988,
      size: 393232,
      rating: null,
      votes: null,
      files: 1,
      kind: 'file',
      matched: true,
      cover: null,
      mtime: 0,
    },
    {
      id: 2,
      name: 'Synthetic Two',
      title: 'The Legend of Zelda',
      igdb: null,
      system: 'nes',
      genres: ['Adventure'],
      tags: [],
      region: 'USA',
      year: 1986,
      size: 131088,
      rating: null,
      votes: null,
      files: 1,
      kind: 'file',
      matched: true,
      cover: null,
      mtime: 0,
    },
  ],
}

describe('v1', () => {
  test('reads_from_the_tag', () => {
    expect(v1Commit()).toMatch(/^[0-9a-f]{40}$/)
    expect(v1Source('app.js')).toContain('function parseQuery(q)')
  })

  test('boots_against_a_fake_api', async () => {
    const v1 = await bootV1({ library })
    try {
      expect(v1.errors).toEqual([])
      expect(v1.evaluate<number>('S.games.length')).toBe(2)
      expect(v1.evaluate<number>('S.filtered.length')).toBe(2)
    } finally {
      v1.close()
    }
  })

  test('exposes_lexical_globals', async () => {
    const v1 = await bootV1({ library })
    try {
      const fmtB = v1.evaluate<(n: number) => string>('fmtB')
      expect(fmtB(1024)).toBe('1.00 KB')
    } finally {
      v1.close()
    }
  })
})
