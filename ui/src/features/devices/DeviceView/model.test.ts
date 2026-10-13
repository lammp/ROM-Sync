import { describe, expect, it } from 'vitest'
import { readinessLine, startOf, systemRows, workIn } from './model'

const systems = [
  { key: 'snes', label: 'Super Nintendo', games: 3, bytes: 30 },
  { key: 'gba', label: 'Game Boy Advance', games: 2, bytes: 20 },
]
const held = [
  { system: 'snes', name: 'A.sfc', size: 10 },
  { system: 'snes', name: 'B.sfc', size: null },
  { system: 'saves', name: 'x.srm', size: 1 },
  { system: 'bios', name: 'scph5501.bin', size: 512 },
]
const systemOf = new Map([
  [1, 'snes'],
  [2, 'snes'],
  [3, 'gba'],
])

describe('the device page model', () => {
  it('rows the store’s systems in key order, then folders the store has no system for, never bios', () => {
    const rows = systemRows(
      systems,
      held,
      { modes: { snes: 'all' }, overrides: { '1': false, '3': true } },
      systemOf,
    )
    expect(
      rows.map((r) => [r.key, r.store?.n ?? null, r.device.n, r.device.bytes, r.mode, r.overrides]),
    ).toEqual([
      ['gba', 2, 0, 0, 'off', 1],
      ['snes', 3, 2, 10, 'all', 1],
      ['saves', null, 1, 1, 'off', 0],
    ])
  })

  it('reads every system as left alone before the selection is read', () => {
    expect(systemRows(systems, [], null, systemOf).map((r) => r.mode)).toEqual(['off', 'off'])
  })

  it('starts the progress from what the plan moves and the games the device holds', () => {
    const plan = {
      send: [{ size: 5 }, { size: 6 }],
      update: [{ size: 4 }],
      remove: [{ size: 9 }],
      bytes: { add: 15, free: 100 },
    }
    expect(startOf(plan, held)).toEqual({ bytesTotal: 15, removesTotal: 1, onDevice: 3, free: 100 })
    expect(workIn(plan)).toBe(4)
    expect(workIn({ ...plan, send: [], update: [], remove: [] })).toBe(0)
  })

  it('says what system files a device lacks, or that it has not been read, or that it has all', () => {
    const labels = { gba: 'Game Boy Advance' }
    expect(
      readinessLine(
        [
          { key: 'gba', readiness: 'missing', missing: ['gba_bios.bin'] },
          { key: 'n64', readiness: 'unknown', missing: [] },
        ],
        labels,
      ),
    ).toEqual({ kind: 'missing', items: ['Game Boy Advance: missing gba_bios.bin'] })
    expect(readinessLine([{ key: 'n64', readiness: 'unknown', missing: [] }], labels)).toEqual({
      kind: 'unread',
    })
    expect(readinessLine([{ key: 'ps2', readiness: 'ready', missing: [] }], labels)).toEqual({
      kind: 'ready',
    })
  })
})
