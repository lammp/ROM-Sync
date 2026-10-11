import { describe, expect, it } from 'vitest'
import type { SysSystem } from '../../../queries/sysfiles/sysfiles'
import { detailOf, heldBySystem, stageRoot } from './model'

const gba: SysSystem = {
  key: 'gba',
  emulator: 'mGBA',
  emulator_seen: true,
  package: 'io.mgba.mgba',
  readiness: 'missing',
  staging: 'absent',
  staging_folder: 'ROM-Sync/bios/gba',
  note: '',
  missing: ['gba_bios.bin'],
  staged_any: false,
  requirements: [
    {
      name: 'gba_bios.bin',
      required: true,
      group: 'bios',
      note: 'n',
      install_label: 'BIOS folder',
      installed_at: 'Android/data/x/bios',
      staged: 'absent',
      installed: 'missing',
      store: { present: true, staged_name: 'gba.bin', size: 16, verified: true },
    },
  ],
}

describe('the system files page model', () => {
  it('counts the device’s games by system, leaving bios out', () => {
    const held = heldBySystem([
      { system: 'gba', size: 10 },
      { system: 'gba', size: null },
      { system: 'BIOS', size: 99 },
    ])
    expect([...held]).toEqual([['gba', { n: 2, bytes: 10 }]])
  })

  it('finds the staging root above the systems’ folders', () => {
    expect(stageRoot([{ staging_folder: 'ROM-Sync/bios/gba' }])).toBe('ROM-Sync/bios')
    expect(stageRoot([])).toBe('')
  })

  it('draws a system with its label, its games and its files', () => {
    const d = detailOf(
      gba,
      { gba: 'Game Boy Advance' },
      new Map([['gba', 300]]),
      new Map([['gba', { n: 2, bytes: 10 }]]),
    )
    expect(d).toMatchObject({
      label: 'Game Boy Advance',
      inStore: 300,
      onDevice: { n: 2, bytes: 10 },
      stagedAny: false,
    })
    expect(d.requirements[0]).toEqual({
      name: 'gba_bios.bin',
      stagedName: 'gba.bin',
      note: 'n',
      required: true,
      group: true,
      store: { present: true, size: 16, verified: true },
      staged: 'absent',
      installed: 'missing',
      installedPath: 'Android/data/x/bios',
    })
    expect(detailOf({ ...gba, key: 'x' }, {}, new Map(), new Map())).toMatchObject({
      label: 'x',
      inStore: 0,
      onDevice: { n: 0, bytes: 0 },
    })
  })
})
