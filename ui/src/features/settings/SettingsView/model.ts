/**
 * The settings page's arrangement (SETTINGS.md): which registry keys sit in
 * which section, in first-run order, what each is called, and turning one
 * section's edits into what is sent. The registry decides every kind and
 * range; a key the page has not placed still appears, under Diagnostics.
 */
import { fromText, type Def, type Scalar } from '../../../lib/settings/settings'

export type Section = {
  readonly id: string
  readonly title: string
  readonly keys: readonly string[]
}

export const SECTIONS: readonly Section[] = [
  { id: 'library', title: 'Library', keys: ['store.root', 'store.rescan_on_launch'] },
  {
    id: 'metadata',
    title: 'Metadata and artwork',
    keys: [
      'igdb.client_id',
      'igdb.client_secret',
      'match.accept_threshold',
      'igdb.requests_per_second',
      'match.auto_libretro_covers',
      'match.auto_enrich',
      'match.abort_after_errors',
    ],
  },
  { id: 'tags', title: 'Tag suggestions', keys: [] },
  {
    id: 'transports',
    title: 'Transports and tools',
    keys: [
      'adb.enabled',
      'adb.path',
      'mtp.enabled',
      'mtp.arrival_floor',
      'mtp.arrival_rate',
      'firmware.folder',
      'device.staging_template',
      'sysfiles.hash_limit',
      'device.probe_interval',
    ],
  },
  {
    id: 'sync',
    title: 'Sync behaviour and guards',
    keys: [
      'plan.free_space_margin',
      'capacity.warn_fraction',
      'capacity.alarm_fraction',
      'sync.confirm_remove_threshold',
      'device.write_marker_after_sync',
      'sync.verify_percentage',
    ],
  },
  {
    id: 'data',
    title: 'Data and storage',
    keys: ['data.directory', 'runs.retention', 'jobs.history_length', 'db.busy_timeout'],
  },
  {
    id: 'diagnostics',
    title: 'Diagnostics',
    keys: ['server.preferred_port', 'server.bind_host', 'log.level'],
  },
]

/** Each key's name on the page; the registry's description is said under it. */
export const LABELS: Readonly<Record<string, string>> = {
  'store.root': 'Store root',
  'store.rescan_on_launch': 'Rescan on launch',
  'igdb.client_id': 'Twitch client ID',
  'igdb.client_secret': 'Client secret',
  'match.accept_threshold': 'Match acceptance threshold',
  'igdb.requests_per_second': 'Requests per second',
  'match.auto_libretro_covers': 'Fill missing covers from libretro after a match',
  'match.auto_enrich': 'Fetch screenshots and tags after a match',
  'match.abort_after_errors': 'Stop a pass after this many errors',
  'adb.enabled': 'Enable ADB transport',
  'adb.path': 'ADB executable',
  'mtp.enabled': 'Enable MTP transport',
  'mtp.arrival_floor': 'Wait at least this long for an MTP copy to arrive',
  'mtp.arrival_rate': 'Assume an MTP copy arrives at least this fast',
  'firmware.folder': 'Firmware folder',
  'device.staging_template': 'Staging path on the device',
  'sysfiles.hash_limit': 'Verify staged files up to',
  'device.probe_interval': 'Device probe interval',
  'plan.free_space_margin': 'Keep free on the device',
  'capacity.warn_fraction': 'Warn at',
  'capacity.alarm_fraction': 'Alarm at',
  'sync.confirm_remove_threshold': 'Confirm a sync that removes at least',
  'device.write_marker_after_sync': 'Write the device marker after every sync',
  'sync.verify_percentage': 'Verify sent files by hash',
  'data.directory': 'Data folder',
  'runs.retention': 'Keep sync run folders',
  'jobs.history_length': 'Keep job history',
  'db.busy_timeout': 'Database busy timeout',
  'server.preferred_port': 'Preferred port',
  'server.bind_host': 'Listen on',
  'log.level': 'Log level',
}

/** The sections with every registry key placed: one the page does not know joins Diagnostics. */
export function arrange(keys: readonly string[]): Section[] {
  const placed = new Set(SECTIONS.flatMap((s) => s.keys))
  const extra = keys.filter((k) => !placed.has(k))
  return SECTIONS.map((s) => ({
    ...s,
    keys: [...s.keys.filter((k) => keys.includes(k)), ...(s.id === 'diagnostics' ? extra : [])],
  }))
}

/** One field's unsaved edit: text, a flag, or "use the default" (sent as null). */
export type Draft = string | boolean | null

/**
 * A section's edits as the engine takes them, or every field that is wrong.
 * Nothing is sent while any field is wrong.
 */
export function toValues(
  drafts: Readonly<Record<string, Draft>>,
  defs: Readonly<Record<string, Def>>,
): { readonly values: Record<string, Scalar> } | { readonly errors: Record<string, string> } {
  const values: Record<string, Scalar> = {}
  const errors: Record<string, string> = {}
  for (const [key, draft] of Object.entries(drafts)) {
    const def = defs[key]
    if (!def) continue
    if (draft === null || typeof draft === 'boolean') {
      values[key] = draft
      continue
    }
    const parsed = fromText(def, draft)
    if (parsed.ok) values[key] = parsed.value
    else errors[key] = parsed.error
  }
  return Object.keys(errors).length ? { errors } : { values }
}

export type SetupFacts = {
  readonly storeSet: boolean
  readonly systems: number
  readonly games: number
  readonly credentials: boolean
}

/** Setup's three steps in first-run order, and whether each is done (SETTINGS.md section 0). */
export function setupDone(f: SetupFacts): readonly [boolean, boolean, boolean] {
  return [f.storeSet && f.systems > 0, f.games > 0, f.credentials]
}
