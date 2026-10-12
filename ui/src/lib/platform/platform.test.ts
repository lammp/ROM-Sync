import { describe, expect, it } from 'vitest'
import { BROWSER, can, hostOf, shellOf } from './platform'

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
})
