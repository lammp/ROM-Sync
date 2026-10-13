/**
 * Notifications (F11-S47): what happened, kept until the person clears it.
 *
 * Three sources feed them. A job that ends, said by kind from its result; a
 * device that connects or disconnects; and the setup steps still to do. A
 * toast still says each event as it happens; the notification is its record.
 * Action feedback ("Library saved", a refusal) stays a toast only: it answers
 * what the person just did, so there is nothing to come back to.
 */
import { formatBytes } from '../format/format'

export type NoticeTone = 'info' | 'warn' | 'bad'
export type NoticeSource = 'setup' | 'job' | 'device'

export type Notice = {
  /** Stable for the event: `job:<id>`, `setup:<step>`, `device:<ref>:<n>`. */
  readonly id: string
  readonly source: NoticeSource
  readonly tone: NoticeTone
  readonly title: string
  readonly body?: string
  /** When it happened, in milliseconds. */
  readonly at: number
  /** Where to act on it, when somewhere does. */
  readonly href?: string
}

/** The most kept; the oldest go first. */
export const KEPT = 100

export type EndedJob = {
  readonly id: string
  readonly kind: string
  readonly state: string
  readonly result?: Readonly<Record<string, number>> | null
  readonly error_message?: string | null
  readonly error_code?: string | null
  readonly finished?: string | null
}

const plural = (n: number, one: string, many = `${one}s`) =>
  `${n.toLocaleString()} ${n === 1 ? one : many}`

/** What the parts of a result say, leaving out what is nothing. */
function parts(r: Readonly<Record<string, number>>, words: readonly [string, string][]): string {
  return words
    .filter(([key]) => (r[key] ?? 0) > 0)
    .map(([key, word]) => `${(r[key] ?? 0).toLocaleString()} ${word}`)
    .join(', ')
}

/** A job's end as a notification; null for one still running. `device` names a device job's device. */
export function jobNotice(job: EndedJob, device?: string): Omit<Notice, 'at'> | null {
  if (job.state !== 'done' && job.state !== 'failed' && job.state !== 'cancelled') return null
  const id = `job:${job.id}`
  const who = device ?? 'the device'
  const what: Readonly<Record<string, string>> = {
    scan: 'Scan',
    match: 'Matching',
    covers: 'Cover fill',
    rematch: 'Rematch',
    franchise: 'Franchise proposals',
    sync: `Sync to ${who}`,
    device: `Reading ${who}`,
    sysfiles: `System files on ${who}`,
    recover: 'Recover',
    maintenance: 'Maintenance',
  }
  const name = what[job.kind] ?? `The ${job.kind} job`
  if (job.state === 'failed')
    return {
      id,
      source: 'job',
      tone: 'bad',
      title: `${name} failed`,
      body: job.error_message ?? job.error_code ?? undefined,
    }
  if (job.state === 'cancelled')
    return { id, source: 'job', tone: 'info', title: `${name} cancelled` }
  const r = job.result ?? {}
  switch (job.kind) {
    case 'scan': {
      const found = (r.added ?? 0) + (r.updated ?? 0) + (r.unchanged ?? 0)
      const body = parts(r, [
        ['added', 'new'],
        ['updated', 'changed'],
        ['removed', 'gone'],
        ['unreadable', 'unreadable'],
      ])
      return {
        id,
        source: 'job',
        tone: (r.unreadable ?? 0) > 0 ? 'warn' : 'info',
        title: `Scan finished: ${plural(found, 'game')} found`,
        body: body || 'nothing changed',
        href: '/',
      }
    }
    case 'match':
      return {
        id,
        source: 'job',
        tone: (r.errors ?? 0) > 0 ? 'warn' : 'info',
        title: `Matching finished: ${plural(r.matched ?? 0, 'game')} matched`,
        body: parts(r, [
          ['unmatched', 'not matched'],
          ['errors', 'failed'],
        ]),
        href: '/',
      }
    case 'covers':
      return {
        id,
        source: 'job',
        tone: (r.failed ?? 0) > 0 ? 'warn' : 'info',
        title: `Covers filled: ${plural(r.filled ?? 0, 'game')}`,
        body: parts(r, [
          ['not_found', 'not found'],
          ['failed', 'failed'],
        ]),
        href: '/',
      }
    case 'franchise':
      return {
        id,
        source: 'job',
        tone: 'info',
        title: `Franchise tags proposed: ${(r.proposed ?? 0).toLocaleString()}`,
        body: 'Each waits for a decision in the game’s details.',
        href: '/',
      }
    case 'sync': {
      const sent = (r.send ?? 0) + (r.update ?? 0)
      const failed = r.failed ?? 0
      return {
        id,
        source: 'job',
        tone: failed > 0 ? 'warn' : 'info',
        title: failed > 0 ? `${who} synced with ${plural(failed, 'failure')}` : `${who} synced`,
        body: [`sent ${sent.toLocaleString()}`, `removed ${(r.remove ?? 0).toLocaleString()}`].join(
          ', ',
        ),
        href: '/devices',
      }
    }
    case 'recover':
      return {
        id,
        source: 'job',
        tone: 'info',
        title: 'Recovered into the store',
        body: r.bytes ? formatBytes(r.bytes) : undefined,
      }
    case 'maintenance':
      return {
        id,
        source: 'job',
        tone: 'info',
        title: 'Maintenance done',
        body: r.bytes ? `${formatBytes(r.bytes)} given back` : undefined,
      }
    default:
      return { id, source: 'job', tone: 'info', title: `${name} finished` }
  }
}

/** A device seen to connect or disconnect. `n` tells one transition from the next. */
export function deviceNotice(
  ref: string,
  name: string,
  connected: boolean,
  n: number,
): Omit<Notice, 'at'> {
  return {
    id: `device:${ref}:${n}`,
    source: 'device',
    tone: 'info',
    title: connected ? `${name} connected` : `${name} disconnected`,
    href: '/devices',
  }
}

export type Setup = {
  readonly storeSet: boolean
  readonly systems: number
  readonly credentials: boolean
}

/** The setup steps still to do, each a notification pointing at its settings tab. */
export function setupNotices(s: Setup): Omit<Notice, 'at'>[] {
  const out: Omit<Notice, 'at'>[] = []
  if (!s.storeSet)
    out.push({
      id: 'setup:store',
      source: 'setup',
      tone: 'warn',
      title: 'Choose your ROMs folder',
      body: 'The library is read from it.',
      href: '/settings#library',
    })
  else if (s.systems === 0)
    out.push({
      id: 'setup:scan',
      source: 'setup',
      tone: 'warn',
      title: 'Read the library',
      body: 'Rescan the ROMs folder to find your games.',
      href: '/settings#library',
    })
  if (!s.credentials)
    out.push({
      id: 'setup:igdb',
      source: 'setup',
      tone: 'info',
      title: 'Add IGDB credentials for covers and details',
      body: 'libretro box art needs no account.',
      href: '/settings#metadata',
    })
  return out
}
