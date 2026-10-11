import { describe, expect, it } from 'vitest'
import { fromText, helpText, isSize, toText, type Def } from './settings'

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
})
