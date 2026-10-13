import { describe, expect, it } from 'vitest'
import {
  deviceKey,
  isOverride,
  isSelected,
  modeOf,
  onDeviceKeys,
  type SelectionState,
} from './selection'

const s: SelectionState = {
  modes: { snes: 'all', nes: 'none' },
  overrides: { '2': false, '3': true },
}

describe('selection, read', () => {
  it('lets an override decide, else the system mode', () => {
    expect(isSelected(s, { id: 1, system: 'snes' })).toBe(true)
    expect(isSelected(s, { id: 2, system: 'snes' })).toBe(false)
    expect(isSelected(s, { id: 3, system: 'nes' })).toBe(true)
    expect(isSelected(s, { id: 4, system: 'nes' })).toBe(false)
  })

  it('selects nothing in an unmanaged system', () => {
    expect(modeOf(s, 'gba')).toBe('off')
    expect(isSelected(s, { id: 5, system: 'gba' })).toBe(false)
  })

  it('knows an override', () => {
    expect([
      isOverride(s, { id: 2, system: 'snes' }),
      isOverride(s, { id: 1, system: 'snes' }),
    ]).toEqual([true, false])
  })

  it('keys the device by system and name, and leaves bios out', () => {
    const keys = onDeviceKeys([
      { system: 'snes', name: 'Super Metroid.sfc' },
      { system: 'bios', name: 'scph5501.bin' },
    ])
    expect([...keys]).toEqual([deviceKey('snes', 'Super Metroid.sfc')])
  })
})
