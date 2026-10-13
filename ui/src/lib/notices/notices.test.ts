import { describe, expect, it } from 'vitest'
import { deviceNotice, jobNotice, setupNotices } from './notices'

const job = (kind: string, result: Record<string, number> = {}, state = 'done') => ({
  id: 'j1',
  kind,
  state,
  result,
})

describe('notices', () => {
  it('says nothing for a job still running', () => {
    expect(jobNotice(job('scan', {}, 'running'))).toBeNull()
    expect(jobNotice(job('scan', {}, 'queued'))).toBeNull()
  })

  it('says how many games a scan found, and what changed', () => {
    expect(jobNotice(job('scan', { added: 3, updated: 1, unchanged: 96, removed: 2 }))).toEqual({
      id: 'job:j1',
      source: 'job',
      tone: 'info',
      title: 'Scan finished: 100 games found',
      body: '3 new, 1 changed, 2 gone',
      href: '/',
    })
    expect(jobNotice(job('scan', { unchanged: 1 }))?.body).toBe('nothing changed')
    expect(jobNotice(job('scan', { unchanged: 5, unreadable: 2 }))?.tone).toBe('warn')
  })

  it('says what metadata passes did', () => {
    expect(jobNotice(job('match', { matched: 7900, unmatched: 13 }))).toMatchObject({
      title: 'Matching finished: 7,900 games matched',
      body: '13 not matched',
      tone: 'info',
    })
    expect(jobNotice(job('match', { matched: 1, errors: 2 }))?.tone).toBe('warn')
    expect(jobNotice(job('covers', { filled: 1, not_found: 4 }))).toMatchObject({
      title: 'Covers filled: 1 game',
      body: '4 not found',
    })
    expect(jobNotice(job('franchise', { proposed: 12 }))?.title).toBe('Franchise tags proposed: 12')
  })

  it('says a sync with its failures as a warning, and names the device', () => {
    expect(jobNotice(job('sync', { send: 4, update: 1, remove: 2 }), 'Thor')).toMatchObject({
      title: 'Thor synced',
      body: 'sent 5, removed 2',
      tone: 'info',
    })
    expect(jobNotice(job('sync', { send: 4, failed: 1 }), 'Thor')).toMatchObject({
      title: 'Thor synced with 1 failure',
      tone: 'warn',
    })
  })

  it('says a failure as an error with its message, and a cancel as such', () => {
    expect(
      jobNotice({ ...job('sync', {}, 'failed'), error_message: 'the device went away' }, 'Thor'),
    ).toMatchObject({ title: 'Sync to Thor failed', body: 'the device went away', tone: 'bad' })
    expect(jobNotice(job('match', {}, 'cancelled'))?.title).toBe('Matching cancelled')
    expect(jobNotice(job('mystery'))?.title).toBe('The mystery job finished')
  })

  it('says a device connecting and disconnecting, each its own notice', () => {
    expect(deviceNotice('R5C', 'Thor', true, 1)).toEqual({
      id: 'device:R5C:1',
      source: 'device',
      tone: 'info',
      title: 'Thor connected',
      href: '/devices',
    })
    expect(deviceNotice('R5C', 'Thor', false, 2).title).toBe('Thor disconnected')
  })

  it('lists the setup steps still to do, each pointing at its tab', () => {
    expect(
      setupNotices({ storeSet: false, systems: 0, credentials: false }).map((n) => [n.id, n.href]),
    ).toEqual([
      ['setup:store', '/settings#library'],
      ['setup:igdb', '/settings#metadata'],
    ])
    expect(
      setupNotices({ storeSet: true, systems: 0, credentials: true }).map((n) => n.id),
    ).toEqual(['setup:scan'])
    expect(setupNotices({ storeSet: true, systems: 4, credentials: true })).toEqual([])
  })
})
