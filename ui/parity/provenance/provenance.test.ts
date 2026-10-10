import { describe, expect, test } from 'vitest'
import { readFixture } from '../fixture/fixture.ts'
import { V1_TAG, v1Commit } from '../v1/v1.ts'
import { findFixtures, ownerData, stringsIn } from './provenance.ts'

describe('provenance', () => {
  test('every_fixture_names_a_tag', () => {
    const commit = v1Commit()
    for (const path of findFixtures()) {
      const { header } = readFixture(path)
      expect(header.tag, path).toBe(V1_TAG)
      expect(header.commit, path).toBe(commit)
      expect(header.corpus, path).not.toBe('')
    }
  })

  test('no_owner_data', () => {
    for (const path of findFixtures()) {
      const { cases } = readFixture(path)
      expect(ownerData(stringsIn(cases)), path).toEqual([])
    }
  })

  test('the_scanner_finds_planted_owner_data', () => {
    const planted = [
      'D:\\Games\\ROMs\\nes',
      'C:/Users/someone/Downloads',
      '/home/someone/roms',
      'bios\\scph1001.bin',
      'Super Mario Bros. 3 (USA).nes',
      'Game (Europe).chd',
      'd41d8cd98f00b204e9800998ecf8427e',
      'USB\\VID_18D1&PID_4EE7',
      '18d1:4ee7',
      'Minerva_Myrient set',
      'No-Intro dat',
    ]
    for (const sample of planted) expect(ownerData([sample]), sample).not.toEqual([])
    expect(ownerData(['Super Mario Bros. 3', 'year>=1990', 'size:10mb', '12 min'])).toEqual([])
  })
})
