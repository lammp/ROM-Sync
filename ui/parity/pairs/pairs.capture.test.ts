import { describe, expect, test } from 'vitest'
import { readRows, versionOneRelations } from './pairs.capture.ts'

describe('pairs capture', () => {
  test('matches_version_1', async () => {
    const rows = readRows()
    const v1 = await versionOneRelations(rows)
    const differ = rows.filter((r, i) => r.relation !== v1[i]?.relation)
    expect(differ, 'committed relations differ from version 1').toEqual([])
  })

  test('sizes_meet_the_corpus_minimum', () => {
    const rows = readRows()
    expect(rows.filter((r) => r.relation !== 'none').length).toBeGreaterThanOrEqual(60)
    expect(rows.filter((r) => r.relation === 'none').length).toBeGreaterThanOrEqual(40)
  })

  test('every_row_names_its_property', () => {
    for (const row of readRows()) expect(row.pins, row.aTitle).not.toBe('')
  })
})
