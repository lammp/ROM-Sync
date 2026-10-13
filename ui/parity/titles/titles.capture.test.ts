import { describe, expect, test } from 'vitest'
import { readRows, versionOneKeys, writeRows } from './titles.capture.ts'

describe('titles capture', () => {
  test('matches_version_1', async () => {
    const rows = readRows()
    expect(rows.length).toBeGreaterThanOrEqual(400)
    const v1 = await versionOneKeys(rows)
    const differ = rows.filter((r, i) => r.strict !== v1[i]?.strict || r.loose !== v1[i]?.loose)
    expect(differ, 'committed keys differ from version 1').toEqual([])
  })

  test('every_row_names_its_property', () => {
    for (const row of readRows()) expect(row.pins, row.title).not.toBe('')
  })

  test('titles_are_unique', () => {
    const titles = readRows().map((r) => r.title)
    expect(new Set(titles).size).toBe(titles.length)
  })

  test('writing_keeps_the_rest_of_the_module', () => {
    const source = 'head\nROWS = r"""\nA\ta\ta\tp\n"""\ntail\n'
    const rows = readRows(source)
    expect(writeRows([{ ...rows[0]!, strict: 'x' }], source)).toBe(
      'head\nROWS = r"""\nA\tx\ta\tp\n"""\ntail\n',
    )
  })
})
