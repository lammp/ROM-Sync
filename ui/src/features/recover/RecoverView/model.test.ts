import { describe, expect, it } from 'vitest'
import { fateOf, orphans } from './model'

const labels = { snes: 'Super Nintendo', n64: 'Nintendo 64' }
const selection = { modes: { snes: 'all', gba: 'none' }, overrides: {} }

describe('the recover page model', () => {
  it('states_removal_consequence: a managed system’s item goes at the next sync; others are left alone, and say why', () => {
    expect(fateOf('snes', selection, labels)).toEqual({ kind: 'removed' })
    expect(fateOf('n64', selection, labels)).toEqual({
      kind: 'left',
      why: 'Nintendo 64 is not managed on this device',
    })
    expect(fateOf('nes', selection, labels)).toEqual({
      kind: 'left',
      why: 'nes is not a store system',
    })
    expect(fateOf('snes', null, labels)).toEqual({
      kind: 'left',
      why: 'Super Nintendo is not managed on this device',
    })
  })

  it('gives every item its fate', () => {
    expect(
      orphans([{ system: 'snes', name: 'A.sfc', kind: 'file', size: 1 }], selection, labels),
    ).toEqual([{ system: 'snes', name: 'A.sfc', kind: 'file', size: 1, fate: { kind: 'removed' } }])
  })
})
