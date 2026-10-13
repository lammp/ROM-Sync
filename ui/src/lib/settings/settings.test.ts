import { describe, expect, it } from 'vitest'
import {
  fromText,
  helpText,
  isSize,
  sizeChoices,
  sizeLabel,
  stepChoices,
  toText,
  type Def,
} from './settings'

const def = (over: Partial<Def>): Def => ({
  kind: 'str',
  unit: '',
  minimum: null,
  maximum: null,
  choices: [],
  ...over,
})
const margin = def({ kind: 'int', unit: ' bytes', minimum: 0, maximum: 8 * 1024 ** 3 })
const port = def({ kind: 'int', minimum: 0, maximum: 65535 })
const ratio = def({ kind: 'float', minimum: 0.1, maximum: 1 })

describe('settings, as the page edits them', () => {
  it('shows and reads sizes as sizes', () => {
    expect(isSize(margin)).toBe(true)
    expect(isSize(port)).toBe(false)
    expect(toText(margin, 512 * 1024 * 1024)).toBe('512.0 MB')
    expect(fromText(margin, '1 gb')).toEqual({ ok: true, value: 1024 ** 3 })
    expect(fromText(margin, 'lots')).toEqual({ ok: false, error: 'A size, such as 512 MB' })
    expect(fromText(margin, '9 GB')).toEqual({ ok: false, error: 'At most 8.00 GB' })
  })

  it('holds numbers to their kind and range', () => {
    expect(fromText(port, ' 8765 ')).toEqual({ ok: true, value: 8765 })
    expect(fromText(port, '1.5')).toEqual({ ok: false, error: 'A whole number' })
    expect(fromText(port, '')).toEqual({ ok: false, error: 'A number' })
    expect(fromText(port, '70000')).toEqual({ ok: false, error: 'At most 65535' })
    expect(fromText(ratio, '0.05')).toEqual({ ok: false, error: 'At least 0.1' })
    expect(fromText(ratio, '0.75')).toEqual({ ok: true, value: 0.75 })
  })

  it('takes text as typed, trimmed, and a choice only from its list', () => {
    expect(fromText(def({ kind: 'path' }), '  D:\\Games\\ROMs ')).toEqual({
      ok: true,
      value: 'D:\\Games\\ROMs',
    })
    const level = def({ choices: ['info', 'debug'] })
    expect(fromText(level, 'debug')).toEqual({ ok: true, value: 'debug' })
    expect(fromText(level, 'loud')).toEqual({ ok: false, error: 'One of info, debug' })
  })

  it('reads the registry’s units as the suffixes they are', () => {
    expect(isSize(def({ kind: 'int', unit: ' B/s' }))).toBe(true)
    expect(
      helpText({
        ...def({ kind: 'float', unit: '/s', minimum: 1, maximum: 4 }),
        description: 'Rate.',
        restart: false,
      }),
    ).toBe('Rate. From 1 to 4/s.')
  })

  it('shows nothing for no value or a flag', () => {
    expect([toText(port, null), toText(def({ kind: 'bool' }), true), toText(port, 80)]).toEqual([
      '',
      '',
      '80',
    ])
  })

  it('says the range and a restart under the field', () => {
    expect(helpText({ ...port, description: 'The port.', restart: true })).toBe(
      'The port. From 0 to 65535. Takes effect after a restart.',
    )
    expect(helpText({ ...margin, description: 'Headroom.', restart: false })).toBe(
      'Headroom. From 0 B to 8.00 GB.',
    )
    expect(
      helpText({
        ...def({ kind: 'int', unit: ' s', minimum: 5, maximum: 300 }),
        description: 'Probe.',
        restart: false,
      }),
    ).toBe('Probe. From 5 to 300 s.')
  })

  it('offers a size setting its powers of two within its bounds, keeping what is stored', () => {
    const MB = 1024 ** 2
    const offered = sizeChoices(margin, 3 * 1024 ** 3)
    expect(offered[0]).toBe(0)
    expect(offered.at(-1)).toBe(8 * 1024 ** 3)
    expect(offered).toContain(512 * MB)
    expect(offered).toContain(3 * 1024 ** 3)
    const limit = def({ kind: 'int', unit: ' bytes', minimum: MB, maximum: 4 * 1024 ** 3 })
    expect(sizeChoices(limit, null)[0]).toBe(MB)
    expect(sizeChoices(def({ kind: 'int', unit: ' bytes' }), 5)).toEqual([])
    expect([
      sizeLabel(margin, 0),
      sizeLabel(margin, 512 * MB),
      sizeLabel(margin, 1024 ** 3),
    ]).toEqual(['none', '512 MB', '1 GB'])
    expect(sizeLabel(def({ kind: 'int', unit: 'B/s' }), 2 * MB)).toBe('2 MB/s')
  })

  it('offers a short range as its whole numbers, keeping what is stored', () => {
    const rate = def({ kind: 'float', unit: '/s', minimum: 1, maximum: 4 })
    expect(stepChoices(rate, 4)).toEqual([1, 2, 3, 4])
    expect(stepChoices(rate, 2.5)).toEqual([1, 2, 2.5, 3, 4])
    expect(stepChoices(def({ kind: 'int' }), 1)).toEqual([])
  })
})
