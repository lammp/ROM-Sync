import { describe, expect, it } from 'vitest'
import { BROWSER, can, hostOf, ranLong, shellOf } from './platform'

describe('platform', () => {
  it('assumes a browser that can ask nothing until the engine answers', () => {
    expect(hostOf(BROWSER)).toBe('browser')
    expect(can(BROWSER, 'pick_folder')).toBe(false)
    expect(can(BROWSER, 'reveal')).toBe(false)
  })

  it('upgrades to the desktop window with what the engine says answers there', () => {
    const shell = shellOf({ kind: 'desktop', capabilities: ['reveal', 'pick_folder'] })
    expect(hostOf(shell)).toBe('desktop window')
    expect(can(shell, 'pick_folder')).toBe(true)
    expect(can(shell, 'open_url')).toBe(false)
  })

  it('keeps the token out of what it describes', () => {
    const session = { token: 't', kind: 'browser' as const, capabilities: [] }
    expect(shellOf(session)).toEqual({ kind: 'browser', capabilities: [] })
  })

  it('calls a job long only past thirty seconds, and only when it has both ends', () => {
    const at = (s: number) => new Date(Date.UTC(2026, 9, 12, 10, 0, s)).toISOString()
    expect(ranLong({ started: at(0), finished: at(31) })).toBe(true)
    expect(ranLong({ started: at(0), finished: at(30) })).toBe(false)
    expect(ranLong({ started: at(0), finished: null })).toBe(false)
    expect(ranLong({ started: null, finished: at(40) })).toBe(false)
    expect(ranLong({ started: 'garbled', finished: at(40) })).toBe(false)
  })
})
