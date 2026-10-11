import { describe, expect, it } from 'vitest'
import { LABELS, SECTIONS, arrange, setupDone, toValues } from './model'

const def = (kind: string, over: object = {}) => ({
  kind,
  unit: '',
  minimum: null,
  maximum: null,
  choices: [],
  ...over,
})

describe('the settings page model', () => {
  it('names every key it places, and places each in one section', () => {
    const placed = SECTIONS.flatMap((s) => s.keys)
    expect(new Set(placed).size).toBe(placed.length)
    expect(placed.filter((k) => !LABELS[k])).toEqual([])
    expect(SECTIONS.map((s) => s.id)).toEqual([
      'library',
      'metadata',
      'tags',
      'transports',
      'sync',
      'data',
      'diagnostics',
    ])
  })

  it('shows a key the page does not know under Diagnostics, and drops one the engine lacks', () => {
    const sections = arrange(['store.root', 'log.level', 'new.thing'])
    expect(sections.find((s) => s.id === 'library')?.keys).toEqual(['store.root'])
    expect(sections.find((s) => s.id === 'diagnostics')?.keys).toEqual(['log.level', 'new.thing'])
  })

  it('turns a section’s edits into values, null for a default, and sends nothing while a field is wrong', () => {
    const defs = {
      'device.probe_interval': def('int', { minimum: 5, maximum: 300 }),
      'plan.free_space_margin': def('int', { unit: ' bytes', minimum: 0, maximum: 8 * 1024 ** 3 }),
      'adb.enabled': def('bool'),
      'adb.path': def('path'),
    }
    expect(
      toValues(
        {
          'device.probe_interval': '30',
          'plan.free_space_margin': '1 GB',
          'adb.enabled': false,
          'adb.path': null,
        },
        defs,
      ),
    ).toEqual({
      values: {
        'device.probe_interval': 30,
        'plan.free_space_margin': 1024 ** 3,
        'adb.enabled': false,
        'adb.path': null,
      },
    })
    expect(toValues({ 'device.probe_interval': '1', 'adb.path': 'x' }, defs)).toEqual({
      errors: { 'device.probe_interval': 'At least 5' },
    })
  })

  it('setup_steps: a store with systems, a read library, and credentials, in that order', () => {
    expect(setupDone({ storeSet: false, systems: 0, games: 0, credentials: false })).toEqual([
      false,
      false,
      false,
    ])
    expect(setupDone({ storeSet: true, systems: 0, games: 0, credentials: true })).toEqual([
      false,
      false,
      true,
    ])
    expect(setupDone({ storeSet: true, systems: 4, games: 40, credentials: false })).toEqual([
      true,
      true,
      false,
    ])
  })
})
