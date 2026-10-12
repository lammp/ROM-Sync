/**
 * The engine, faked: one world of games, devices and settings, and the API's
 * answers computed from it. Playwright serves it over HTTP (e2e/serve.ts);
 * stories hand it to the engine client as its fetch. Pure TypeScript, so it
 * runs in Node and in the browser alike. Every title is invented.
 */

type Json = Record<string, unknown>
export type Answer = { readonly status: number; readonly body: unknown }

export type Game = {
  id: number
  system: string
  name: string
  title: string
  region: string | null
  kind: string
  size: number
  mtime: number
  files: number
  state: string
  matched: boolean
  confidence: number | null
  igdb_id: number | null
  igdb_name: string | null
  year: number | null
  genres: string[]
  rating: number | null
  votes: number | null
  cover: string | null
  tags: Record<string, string[]>
}

export type Tag = { tag: string; kind: string; state: string; source: string | null }

export type World = {
  systems: { key: string; label: string; extensions: string[] }[]
  games: Game[]
  tags: Record<number, Tag[]>
  /** Settings stored by key; anything absent is the registry's default. */
  stored: Record<string, unknown>
  /** The stored client secret, which no answer ever carries. */
  secret: string | null
  profiles: Json[]
  attached: Json[]
  blocked: { kind: string; description: string; reason: string }[]
  selections: Record<string, { modes: Record<string, string>; overrides: Record<string, boolean> }>
  inventory: Record<string, { system: string; name: string; kind: string; size: number | null }[]>
  runs: Record<string, Json[]>
  capacity: Record<string, { total: number; free: number }>
  jobs: Json[]
  nextJob: number
  /** A sync per device reference; each status read moves it on one step. */
  syncs: Record<string, { job: Json; run: Json; step: number; plan: Json; id: string }>
  /** Each device's system files: whether it has been read, what is staged, what is stray. */
  sysfiles: Record<
    string,
    { surveyed: string | null; staged: Record<string, boolean>; others: Json[] }
  >
  /** Maintenance actions run, whose dry runs now find nothing. */
  maintained: string[]
  /** Reads that fail, by path prefix, as an engine that does not answer would. */
  failing: string[]
  /** Files in the store's folders the library has not read yet, by system and name. */
  unread: { system: string; name: string; size: number }[]
  nextRun: number
  /** Who hosts the page: a browser on loopback, as the e2e suite runs, unless a case says otherwise. */
  shell: {
    kind: 'desktop' | 'browser'
    capabilities: ('reveal' | 'pick_folder' | 'open_url' | 'notify')[]
  }
  /** System notifications the page asked for, by text. */
  notified: string[]
  /** Each transport's state on the last probe, as the engine reports it (F13-S8). */
  transports: { kind: string; available: boolean; detail: string }[]
}

const MB = 1 << 20
const SYSTEMS = [
  { key: 'snes', label: 'Super Nintendo', extensions: ['.sfc'] },
  { key: 'gba', label: 'Game Boy Advance', extensions: ['.gba'] },
  { key: 'n64', label: 'Nintendo 64', extensions: ['.z64'] },
  { key: 'ps2', label: 'PlayStation 2', extensions: ['.iso'] },
]
const WORDS = [
  'Star',
  'Quest',
  'Racer',
  'Knight',
  'Island',
  'Galaxy',
  'Puzzle',
  'Dragon',
  'Shadow',
  'Rally',
]
const GENRES = ['Platform', 'Role-playing (RPG)', 'Racing', 'Puzzle', 'Adventure']
const REGIONS = ['USA', 'Europe', 'Japan', 'USA, Europe']

/** Forty invented games across four systems, the same every time. */
function games(): Game[] {
  return Array.from({ length: 40 }, (_, i) => {
    const system = SYSTEMS[i % 4]?.key ?? 'snes'
    const title = `${WORDS[i % 10]} ${WORDS[(i * 3 + 1) % 10]} ${Math.floor(i / 10) + 1}`
    const ext = SYSTEMS[i % 4]?.extensions[0] ?? '.bin'
    return {
      id: i + 1,
      system,
      name: `${title} (${REGIONS[i % 4]})${ext}`,
      title,
      region: REGIONS[i % 4] ?? null,
      kind: system === 'ps2' && i % 8 === 3 ? 'folder' : 'file',
      size: (i + 1) * 3 * MB,
      mtime: 1_700_000_000 + i * 86_400,
      files: system === 'ps2' && i % 8 === 3 ? 2 : 1,
      state: i % 5 === 4 ? 'pending' : 'matched',
      matched: i % 5 !== 4,
      confidence: i % 5 === 4 ? null : 0.9,
      igdb_id: i % 5 === 4 ? null : 1000 + i,
      igdb_name: i % 5 === 4 ? null : title,
      year: i % 5 === 4 ? null : 1990 + (i % 20),
      genres: i % 5 === 4 ? [] : [GENRES[i % 5] ?? 'Platform'],
      rating: i % 5 === 4 ? null : 60 + (i % 35),
      votes: i % 5 === 4 ? null : 10 + i * 3,
      cover: null,
      tags: i % 3 === 0 ? { franchise: [String(WORDS[i % 10])] } : ({} as Record<string, string[]>),
    }
  })
}

/** The engine's settings registry as GET /settings describes it (engine/romsync/config/registry.py). */
const REGISTRY: readonly Json[] = [
  {
    key: 'store.root',
    kind: 'path',
    default: '',
    description: 'The front-end ROMs folder the library is read from.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'store.rescan_on_launch',
    kind: 'bool',
    default: false,
    description: 'Rescan the store every time the application starts.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'data.directory',
    kind: 'path',
    default: '',
    description:
      'Where the database, covers and logs live. Chosen at first run, outside the install folder, so replacing the application cannot touch it.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: true,
    secret: false,
  },
  {
    key: 'adb.enabled',
    kind: 'bool',
    default: true,
    description: 'Offer devices over the Android debug bridge.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'adb.path',
    kind: 'path',
    default: '',
    description:
      'The debug bridge executable. Empty means look on the PATH; absent disables the transport and is stated in Settings, not an error.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'mtp.enabled',
    kind: 'bool',
    default: true,
    description: 'Offer devices over the media transfer protocol.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'mtp.arrival_floor',
    kind: 'int',
    default: 600,
    description:
      'Seconds a copy to a media-transfer device may sit without growing before it counts as stalled, however small the file. Used for every copy, staged or bulk.',
    choices: [],
    minimum: 60,
    maximum: 7200,
    unit: ' s',
    restart: false,
    secret: false,
  },
  {
    key: 'mtp.arrival_rate',
    kind: 'int',
    default: 2097152,
    description:
      'The slowest rate a copy to a media-transfer device is allowed: a larger file is given its size divided by this, in seconds, if that exceeds the floor.',
    choices: [],
    minimum: 65536,
    maximum: 1073741824,
    unit: ' B/s',
    restart: false,
    secret: false,
  },
  {
    key: 'device.probe_interval',
    kind: 'int',
    default: 15,
    description: 'Seconds between probes while a device page is open.',
    choices: [],
    minimum: 5,
    maximum: 300,
    unit: ' s',
    restart: false,
    secret: false,
  },
  {
    key: 'device.staging_template',
    kind: 'str',
    default: 'ROM-Sync/{system}',
    description: "Where a system's files are staged on a device. Must contain {system}.",
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'device.write_marker_after_sync',
    kind: 'bool',
    default: true,
    description: 'Rewrite the identity marker on the device after a successful sync.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'sysfiles.hash_limit',
    kind: 'int',
    default: 67108864,
    description: 'Files larger than this are compared by size, not by hash.',
    choices: [],
    minimum: 1048576,
    maximum: 4294967296,
    unit: ' bytes',
    restart: false,
    secret: false,
  },
  {
    key: 'firmware.folder',
    kind: 'path',
    default: '',
    description: 'Where firmware and key files are read from. Nothing is ever fetched.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'plan.free_space_margin',
    kind: 'int',
    default: 536870912,
    description: 'Headroom kept free on a destination after a sync.',
    choices: [],
    minimum: 0,
    maximum: 8589934592,
    unit: ' bytes',
    restart: false,
    secret: false,
  },
  {
    key: 'capacity.warn_fraction',
    kind: 'float',
    default: 0.8,
    description: 'Fill fraction at which the capacity meter turns to caution.',
    choices: [],
    minimum: 0.1,
    maximum: 1.0,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'capacity.alarm_fraction',
    kind: 'float',
    default: 0.9,
    description: 'Fill fraction at which it turns to alarm.',
    choices: [],
    minimum: 0.1,
    maximum: 1.0,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'sync.confirm_remove_threshold',
    kind: 'int',
    default: 25,
    description: 'A plan removing more than this many items asks twice.',
    choices: [],
    minimum: 0,
    maximum: 100000,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'sync.verify_percentage',
    kind: 'int',
    default: 100,
    description: 'How much of a transfer is content-verified where the transport allows it.',
    choices: [],
    minimum: 0,
    maximum: 100,
    unit: ' %',
    restart: false,
    secret: false,
  },
  {
    key: 'igdb.client_id',
    kind: 'str',
    default: '',
    description: 'The metadata service client identifier.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'igdb.client_secret',
    kind: 'str',
    default: '',
    description: 'The metadata service client secret. Never returned by the API.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: true,
  },
  {
    key: 'igdb.requests_per_second',
    kind: 'float',
    default: 4.0,
    description: 'Shared request budget across every concurrent pass. IGDB allows four.',
    choices: [],
    minimum: 1.0,
    maximum: 4.0,
    unit: '/s',
    restart: false,
    secret: false,
  },
  {
    key: 'match.accept_threshold',
    kind: 'float',
    default: 0.55,
    description: 'Score at or above which a candidate is accepted as a match.',
    choices: [],
    minimum: 0.0,
    maximum: 1.0,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'match.abort_after_errors',
    kind: 'int',
    default: 25,
    description: 'A matching pass stops after this many failures in a row.',
    choices: [],
    minimum: 1,
    maximum: 1000,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'match.auto_libretro_covers',
    kind: 'bool',
    default: true,
    description: 'Fill a missing cover from the community thumbnail set. Never replaces one.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'match.auto_enrich',
    kind: 'bool',
    default: false,
    description: 'Fetch screenshots and tags for a matched game without being asked.',
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'server.preferred_port',
    kind: 'int',
    default: 8765,
    description: 'The loopback port to try first. Zero means ask the operating system.',
    choices: [],
    minimum: 0,
    maximum: 65535,
    unit: '',
    restart: true,
    secret: false,
  },
  {
    key: 'server.bind_host',
    kind: 'str',
    default: '127.0.0.1',
    description: 'Binding anywhere but loopback disables the shell endpoints and logs why.',
    choices: ['127.0.0.1', '0.0.0.0'],
    minimum: null,
    maximum: null,
    unit: '',
    restart: true,
    secret: false,
  },
  {
    key: 'log.level',
    kind: 'str',
    default: 'info',
    description: 'How much the application writes to its log.',
    choices: ['debug', 'info', 'warning', 'error'],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'jobs.history_length',
    kind: 'int',
    default: 200,
    description: 'Terminal jobs kept before the oldest are evicted.',
    choices: [],
    minimum: 10,
    maximum: 10000,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'runs.retention',
    kind: 'int',
    default: 50,
    description: 'Run folders kept on disk before the oldest are pruned.',
    choices: [],
    minimum: 1,
    maximum: 1000,
    unit: '',
    restart: false,
    secret: false,
  },
  {
    key: 'db.busy_timeout',
    kind: 'int',
    default: 5000,
    description: 'How long a writer waits for the database lock.',
    choices: [],
    minimum: 100,
    maximum: 60000,
    unit: ' ms',
    restart: false,
    secret: false,
  },
]

/** Every setting as GET /settings answers: the stored value over the default; a secret never. */
function describe(w: World): Json[] {
  return REGISTRY.map((r) => {
    const key = String(r.key)
    const stored = key in w.stored
    if (r.secret)
      return {
        ...r,
        default: null,
        value: null,
        stored: w.secret !== null,
        secret_state: {
          present: w.secret !== null,
          length: w.secret?.length ?? 0,
          saved_at: w.secret ? '2026-10-08T04:11:00+00:00' : null,
          source: w.secret ? 'typed' : null,
        },
      }
    return { ...r, value: stored ? w.stored[key] : r.default, stored, secret_state: null }
  })
}

/** POST /settings: every key checked before any is stored, as the engine does; null deletes. */
function writeSettings(w: World, values: Record<string, unknown>): Answer {
  for (const [key, value] of Object.entries(values)) {
    const r = REGISTRY.find((x) => x.key === key)
    if (!r) return error(422, 'config.unknown_key', `no setting ${key}`, key)
    if (value === null || r.secret) continue
    const kind = String(r.kind)
    const n = typeof value === 'number' ? value : NaN
    if (
      kind === 'bool'
        ? typeof value !== 'boolean'
        : kind === 'int' || kind === 'float'
          ? Number.isNaN(n) || (kind === 'int' && !Number.isInteger(n))
          : typeof value !== 'string'
    )
      return error(422, 'config.wrong_type', `${key} takes a ${kind}`, key)
    if (
      (r.minimum !== null && n < Number(r.minimum)) ||
      (r.maximum !== null && n > Number(r.maximum))
    )
      return error(
        422,
        'config.out_of_range',
        `${key} must be between ${String(r.minimum)} and ${String(r.maximum)}`,
        key,
      )
    if ((r.choices as string[]).length && !(r.choices as string[]).includes(String(value)))
      return error(
        422,
        'config.out_of_range',
        `${key} must be one of ${(r.choices as string[]).join(', ')}`,
        key,
      )
  }
  for (const [key, value] of Object.entries(values)) {
    const r = REGISTRY.find((x) => x.key === key)
    if (r?.secret) w.secret = value === null || value === '' ? null : String(value)
    else if (value === null) delete w.stored[key]
    else w.stored[key] = value
  }
  return { status: 200, body: { settings: describe(w) } }
}

export const THOR_REF = 'YWRiAHNlcmlhbC0x'
/** A drive plugged in with no profile, and a handheld carrying another computer's marker. */
export const CARD_REF = 'dm9sdW1lAGNhcmQ'
export const RETROID_REF = 'YWRiAHNlcmlhbC0y'

export function freshWorld(): World {
  const all = games()
  return {
    systems: SYSTEMS,
    games: all,
    tags: {
      1: [
        { tag: 'Star', kind: 'franchise', state: 'accepted', source: 'rules' },
        { tag: 'Space opera', kind: 'theme', state: 'proposed', source: 'rules' },
      ],
    },
    stored: { 'store.root': 'D:\\Games\\ROMs' },
    secret: null,
    profiles: [
      {
        id: 'dev-1',
        name: 'Thor',
        kind: 'adb',
        roms_root: '/storage/emulated/0/ROMs',
        first_seen: '2026-09-01T10:00:00',
        last_seen: '2026-10-10T10:00:00',
        capacity: 256 * 1024 * MB,
        free: 120 * 1024 * MB,
        ref: THOR_REF,
      },
      {
        id: 'dev-2',
        name: 'Deck card',
        kind: 'volume',
        roms_root: 'ROMs',
        first_seen: '2026-08-01T09:00:00',
        last_seen: '2026-09-20T18:30:00',
        capacity: 512 * 1024 * MB,
        free: 300 * 1024 * MB,
        ref: null,
      },
    ],
    attached: [
      {
        ref: THOR_REF,
        kind: 'adb',
        description: 'AYN Thor (serial-1)',
        has_marker: true,
        roms_root: '/storage/emulated/0/ROMs',
      },
      {
        ref: CARD_REF,
        kind: 'volume',
        description: 'SD card (E:)',
        has_marker: false,
        roms_root: 'ROMs',
      },
      {
        ref: RETROID_REF,
        kind: 'adb',
        description: 'Retroid (serial-2)',
        has_marker: true,
        roms_root: '/storage/emulated/0/ROMs',
      },
    ],
    blocked: [{ kind: 'adb', description: 'Android device (serial-3)', reason: 'unauthorized' }],
    selections: {
      'dev-1': { modes: { snes: 'all', gba: 'none' }, overrides: { '2': true } },
      'dev-2': { modes: { n64: 'all' }, overrides: {} },
    },
    inventory: {
      'dev-1': [
        { system: 'snes', name: String(all[0]?.name), kind: 'file', size: all[0]?.size ?? 0 },
        { system: 'bios', name: 'scph5501.bin', kind: 'sysfile', size: 524_288 },
      ],
      'dev-2': [],
    },
    runs: { 'dev-1': [], 'dev-2': [] },
    capacity: {
      [THOR_REF]: { total: 256 * 1024 * MB, free: 120 * 1024 * MB },
      [CARD_REF]: { total: 512 * 1024 * MB, free: 500 * 1024 * MB },
      [RETROID_REF]: { total: 128 * 1024 * MB, free: 64 * 1024 * MB },
    },
    jobs: [],
    nextJob: 1,
    syncs: {},
    sysfiles: {},
    maintained: [],
    failing: [],
    unread: [],
    nextRun: 1,
    shell: { kind: 'browser', capabilities: ['reveal', 'pick_folder', 'open_url', 'notify'] },
    notified: [],
    transports: [
      { kind: 'volume', available: true, detail: '1 drive(s)' },
      { kind: 'mtp', available: true, detail: '0 storage(s)' },
      { kind: 'adb', available: true, detail: '2 device(s)' },
    ],
  }
}

const error = (
  status: number,
  code: string,
  message: string,
  field: string | null = null,
): Answer => ({
  status,
  body: { error: { code, message, field } },
})

function selected(w: World, deviceId: string, g: Game): boolean {
  const s = w.selections[deviceId]
  if (!s) return false
  const o = s.overrides[String(g.id)]
  return o !== undefined ? o : s.modes[g.system] === 'all'
}

/** The registry, cut down: what each fake system's emulator needs. */
const SYSFILES: Record<
  string,
  {
    emulator: string
    package: string
    files: { name: string; required: boolean; size: number; verified: boolean | null; at: string }[]
  }
> = {
  gba: {
    emulator: 'mGBA',
    package: 'io.mgba.mgba',
    files: [
      {
        name: 'gba_bios.bin',
        required: true,
        size: 16_384,
        verified: true,
        at: 'Android/data/io.mgba.mgba/files/bios',
      },
    ],
  },
  ps2: {
    emulator: 'NetherSX2',
    package: 'xyz.aethersx2.android',
    files: [
      {
        name: 'scph39001.bin',
        required: true,
        size: 4_194_304,
        verified: false,
        at: 'Android/data/xyz.aethersx2.android/files/bios',
      },
    ],
  },
  snes: { emulator: 'Snes9x', package: 'com.explusalpha.Snes9xPlus', files: [] },
  n64: { emulator: 'Mupen64Plus', package: 'org.mupen64plusae.v3.fzurita', files: [] },
}
const STAGE_ROOT = 'ROM-Sync/bios'

function sysfilesOf(w: World, ref: string) {
  return (w.sysfiles[ref] ??= { surveyed: null, staged: {}, others: [] })
}

/** A device's readiness as the engine reports it from its last survey. */
function sysReport(w: World, ref: string): Answer {
  if (!w.profiles.some((p) => p.ref === ref))
    return error(404, 'profile.not_found', 'this device has no profile yet', 'device')
  const d = sysfilesOf(w, ref)
  const read = d.surveyed !== null
  const systems = Object.entries(SYSFILES).map(([key, s]) => {
    const staged = Boolean(d.staged[key])
    // ps2's file is installed already; gba's never is until the person installs it on the device
    const installed = key === 'ps2'
    const requirements = s.files.map((f) => ({
      name: f.name,
      required: f.required,
      group: null,
      note: '',
      install_label: 'BIOS folder',
      installed_at: f.at,
      staged: !read ? 'unknown' : staged ? 'current' : 'absent',
      installed: !read ? 'unknown' : installed ? 'installed' : 'missing',
      store: { present: true, staged_name: f.name, size: f.size, verified: f.verified },
    }))
    const readiness = !s.files.length ? 'none' : !read ? 'unknown' : installed ? 'ready' : 'missing'
    return {
      key,
      emulator: s.emulator,
      emulator_seen: read ? true : null,
      package: read ? s.package : null,
      readiness,
      staging: !s.files.length
        ? 'nothing_to_stage'
        : !read
          ? 'unknown'
          : staged
            ? 'current'
            : 'absent',
      staging_folder: `${STAGE_ROOT}/${key}`,
      note: '',
      requirements,
      missing: readiness === 'missing' ? s.files.map((f) => f.name) : [],
      staged_any: staged,
    }
  })
  return { status: 200, body: { surveyed_at: d.surveyed, apps: {}, systems, others: d.others } }
}

type PlanOp = { system: string; name: string; kind: string; size: number }

/** The engine's threshold for asking a removal count to be confirmed (sync.confirm_remove_threshold). */
const CONFIRM_REMOVALS = 25

function startSync(w: World, ref: string, confirm: unknown): Answer {
  const planned = plan(w, ref)
  if (planned.status !== 200) return planned
  const body = planned.body as Json & { send: PlanOp[]; remove: PlanOp[]; bytes: Json }
  const running = w.syncs[ref]
  if (running && running.job.state === 'running')
    return error(409, 'job.conflict', 'a sync job is already running on that target', 'kind')
  if (body.bytes.fits === false)
    return error(
      409,
      'plan.does_not_fit',
      "the plan's peak use is more than the device's free space",
    )
  const removals = body.remove.length
  if (removals && removals >= CONFIRM_REMOVALS && confirm !== removals)
    return error(
      409,
      'sync.confirm_removals',
      `this sync removes ${removals} games; confirm that number to start it`,
      'confirm_removals',
    )
  const id = String(body.device_id)
  const total = body.send.length + body.remove.length
  const job: Json = {
    id: `job-${w.nextJob++}`,
    kind: 'sync',
    target: ref,
    state: 'running',
    progress: {
      phase: 'send',
      done: 0,
      total,
      current: body.send[0]?.name ?? null,
      detail: { bytes_done: 0, bytes_removed: 0, sent: 0, removed: 0 },
    },
    result: null,
    error_code: null,
    error_message: null,
    started: '2026-10-11T12:00:00',
    finished: null,
  }
  const run: Json = {
    id: w.nextRun++,
    started: '2026-10-11T12:00:00',
    finished: null,
    state: 'running',
    counts: null,
    bytes_moved: null,
  }
  w.jobs.push(job)
  ;(w.runs[id] ??= []).unshift(run)
  w.syncs[ref] = { job, run, step: 0, plan: body, id }
  return { status: 200, body: job }
}

/**
 * Named states a spec or story starts from. "recover": Thor holds three items
 * the library lacks (one in a managed system, one in a system it leaves
 * alone, one in a folder the store has no system for) and a fourth whose
 * name the store's folder already has, unread.
 */
export function seed(w: World, scenario: string): void {
  if (scenario !== 'recover') throw new Error(`no scenario ${scenario}`)
  w.inventory['dev-1']?.push(
    { system: 'snes', name: 'Hidden Gem (USA).sfc', kind: 'file', size: 2 * MB },
    { system: 'snes', name: 'Clash (USA).sfc', kind: 'file', size: MB },
    { system: 'n64', name: 'Translation Patch', kind: 'folder', size: null },
    { system: 'nes', name: 'Homebrew.nes', kind: 'file', size: 40_960 },
  )
  w.unread.push({ system: 'snes', name: 'Clash (USA).sfc', size: MB })
}

function recoverList(w: World, ref: string): Answer {
  const p = w.profiles.find((x) => x.ref === ref)
  if (!p) return error(404, 'profile.not_found', 'this device has no profile yet', 'device')
  const library = new Set(w.games.map((g) => `${g.system}\\${g.name}`))
  const items = (w.inventory[String(p.id)] ?? []).filter(
    (i) => i.kind !== 'sysfile' && i.system !== 'bios' && !library.has(`${i.system}\\${i.name}`),
  )
  return { status: 200, body: { items } }
}

function failedJob(w: World, kind: string, target: string, code: string, message: string): Answer {
  const view = job(w, kind, target)
  const body = view.body as Json
  body.state = 'failed'
  body.result = null
  body.error_code = code
  body.error_message = message
  return view
}

/** One status read: half way on the first, finished on the second, as the engine would report it. */
function syncStatus(w: World, ref: string): Answer {
  const s = w.syncs[ref]
  if (!s) return { status: 200, body: { job: null, run: null } }
  const { job, run, plan: p, id } = s
  const send = p.send as PlanOp[]
  const remove = p.remove as PlanOp[]
  if (job.state === 'running') {
    s.step++
    const sent = s.step === 1 ? Math.floor(send.length / 2) : send.length
    const bytes = send.slice(0, sent).reduce((a, o) => a + o.size, 0)
    const removed = s.step === 1 ? 0 : remove.length
    job.progress = {
      phase: s.step === 1 ? 'send' : 'remove',
      done: sent + removed,
      total: send.length + remove.length,
      current: send[sent]?.name ?? null,
      detail: {
        bytes_done: bytes,
        bytes_removed: remove.slice(0, removed).reduce((a, o) => a + o.size, 0),
        sent,
        removed,
      },
    }
    if (s.step >= 2) {
      const gone = new Set(remove.map((o) => `${o.system}\\${o.name}`))
      const held = (w.inventory[id] ?? []).filter((i) => !gone.has(`${i.system}\\${i.name}`))
      held.push(
        ...send.map((o) => ({ system: o.system, name: o.name, kind: o.kind, size: o.size })),
      )
      w.inventory[id] = held
      const counts = { done: send.length + remove.length, send: send.length, remove: remove.length }
      job.state = 'done'
      job.finished = '2026-10-11T12:01:00'
      job.result = { run: Number(run.id), ...counts }
      run.state = 'done'
      run.finished = '2026-10-11T12:01:00'
      run.counts = counts
      run.bytes_moved = bytes
    }
  }
  return { status: 200, body: { job, run } }
}

function plan(w: World, ref: string): Answer {
  const profile = w.profiles.find((p) => p.ref === ref)
  if (!profile) return error(404, 'profile.not_found', 'this device has no profile yet')
  const id = String(profile.id)
  const items = w.inventory[id] ?? []
  const on = new Set(items.map((i) => `${i.system}\\${i.name}`))
  const managed = Object.entries(w.selections[id]?.modes ?? {})
    .filter(([, m]) => m !== 'off')
    .map(([s]) => s)
  const op = (action: string) => (g: Game) => ({
    action,
    system: g.system,
    name: g.name,
    kind: g.kind,
    size: g.size,
    game_id: g.id,
  })
  const send = w.games
    .filter((g) => selected(w, id, g) && !on.has(`${g.system}\\${g.name}`))
    .map(op('send'))
  const remove = w.games
    .filter(
      (g) => managed.includes(g.system) && !selected(w, id, g) && on.has(`${g.system}\\${g.name}`),
    )
    .map(op('remove'))
  const add = send.reduce((a, o) => a + o.size, 0)
  const drop = remove.reduce((a, o) => a + o.size, 0)
  const free = w.capacity[ref]?.free ?? null
  return {
    status: 200,
    body: {
      device_id: id,
      send,
      update: [],
      remove,
      unchanged: items.filter((i) => i.system !== 'bios').length - remove.length,
      unknown_systems: {},
      managed_systems: managed,
      bytes: {
        add,
        drop,
        net: add - drop,
        peak: add,
        free,
        fits: free == null ? null : add + 512 * MB <= free,
      },
    },
  }
}

/** A profile for an attached device, as the engine makes one: empty selection, nothing held. */
function makeProfile(w: World, found: Json, id: string, name: string): Json {
  const now = '2026-10-11T12:00:00'
  const profile = {
    id,
    name,
    kind: found.kind,
    roms_root: found.roms_root,
    first_seen: now,
    last_seen: now,
    capacity: w.capacity[String(found.ref)]?.total ?? null,
    free: w.capacity[String(found.ref)]?.free ?? null,
    ref: found.ref,
  }
  w.profiles.push(profile)
  w.selections[id] = { modes: {}, overrides: {} }
  w.inventory[id] = []
  w.runs[id] = []
  found.has_marker = true
  return profile
}

function selectionView(w: World, id: string): Answer {
  const s = w.selections[id]
  return s
    ? { status: 200, body: { device_id: id, ...s } }
    : error(404, 'profile.not_found', `no device profile ${id}`, 'device_id')
}

function job(
  w: World,
  kind: string,
  target: string | null,
  result: Record<string, number> = { done: 1 },
): Answer {
  const view = {
    id: `job-${w.nextJob++}`,
    kind,
    target,
    state: 'done',
    progress: null,
    result,
    error_code: null,
    error_message: null,
    started: null,
    finished: null,
  }
  w.jobs.push(view)
  return { status: 200, body: view }
}

type Route = {
  method: string
  pattern: RegExp
  handle: (w: World, params: string[], body: Json) => Answer
}

const route = (method: string, path: string, handle: Route['handle']): Route => ({
  method,
  pattern: new RegExp(`^${path.replace(/\{[^}]+\}/g, '([^/]+)')}$`),
  handle,
})

const ROUTES: Route[] = [
  route('GET', '/api/v1/version', () => ({
    status: 200,
    body: { application: 'ROM-Sync', version: '2.0.0.dev0', api: 'v1' },
  })),
  route('GET', '/api/v1/session', (w) => ({
    status: 200,
    body: { token: 'e2e-token', ...w.shell },
  })),
  route('POST', '/api/v1/shell/notify', (w, _m, body) => {
    w.notified.push(String((body as { body?: unknown } | null)?.body ?? ''))
    return { status: 200, body: { delivered: true } }
  }),
  route('GET', '/api/v1/library', (w) => ({ status: 200, body: { games: w.games } })),
  route('GET', '/api/v1/systems', (w) => ({
    status: 200,
    body: {
      systems: w.systems.map((s) => {
        const mine = w.games.filter((g) => g.system === s.key)
        return { ...s, games: mine.length, bytes: mine.reduce((a, g) => a + g.size, 0) }
      }),
    },
  })),
  route('GET', '/api/v1/games/{id}', (w, [id]) => {
    const g = w.games.find((x) => x.id === Number(id))
    return g
      ? { status: 200, body: { ...g, summary: `${g.title}, invented for the tests.`, members: [] } }
      : error(404, 'game.not_found', `no game ${id}`)
  }),
  route('GET', '/api/v1/games/{id}/tags', (w, [id]) => ({
    status: 200,
    body: { game_id: Number(id), tags: w.tags[Number(id)] ?? [] },
  })),
  route('POST', '/api/v1/games/{id}/tags', (w, [id], b) => {
    const list = (w.tags[Number(id)] ??= [])
    list.push({
      tag: String(b.tag),
      kind: String(b.kind ?? 'user'),
      state: 'accepted',
      source: 'user',
    })
    return { status: 200, body: { game_id: Number(id), tags: list } }
  }),
  route('POST', '/api/v1/games/{id}/tags/decide', (w, [id], b) => {
    const list = (w.tags[Number(id)] ??= [])
    const t = list.find((x) => x.tag === b.tag && x.kind === b.kind)
    if (t) t.state = b.accept ? 'accepted' : 'rejected'
    return {
      status: 200,
      body: { game_id: Number(id), tags: list },
    }
  }),
  route('POST', '/api/v1/games/{id}/tags/remove', (w, [id], b) => {
    w.tags[Number(id)] = (w.tags[Number(id)] ?? []).filter(
      (x) => !(x.tag === b.tag && x.kind === b.kind),
    )
    return { status: 200, body: { game_id: Number(id), tags: w.tags[Number(id)] } }
  }),
  route('POST', '/api/v1/games/{id}/rematch', (w, [id]) => job(w, 'rematch', `game:${id}`)),
  route('GET', '/api/v1/settings', (w) => ({ status: 200, body: { settings: describe(w) } })),
  route('POST', '/api/v1/settings', (w, _p, b) =>
    writeSettings(w, (b.values ?? {}) as Record<string, unknown>),
  ),
  route('POST', '/api/v1/igdb/test', (w, _p, b) => {
    const id = b.client_id ?? w.stored['igdb.client_id'] ?? ''
    const secret = b.client_secret ?? w.secret
    if (!id || !secret)
      return {
        status: 200,
        body: {
          ok: false,
          failed_at: 'missing',
          stages: [
            {
              name: 'missing',
              outcome: 'failed',
              code: 'metadata.credentials_missing',
              message: 'Add a client ID and secret first',
            },
          ],
        },
      }
    if (String(secret).length < 20)
      return {
        status: 200,
        body: {
          ok: false,
          failed_at: 'token',
          stages: [
            {
              name: 'token',
              outcome: 'failed',
              code: 'metadata.rejected',
              message: 'Twitch rejected the credentials',
            },
          ],
        },
      }
    return {
      status: 200,
      body: {
        ok: true,
        failed_at: null,
        stages: [
          { name: 'token', outcome: 'ok', code: null, message: null },
          { name: 'api', outcome: 'ok', code: null, message: null },
        ],
      },
    }
  }),
  route('GET', '/api/v1/jobs', (w) => ({ status: 200, body: { jobs: [...w.jobs].reverse() } })),
  route('POST', '/api/v1/jobs/{id}/cancel', (w, [id]) => {
    const j = w.jobs.find((x) => x.id === id)
    if (!j) return error(404, 'job.not_found', `no job ${id}`)
    if (j.state === 'running' || j.state === 'queued') j.state = 'cancelled'
    return { status: 200, body: j }
  }),
  route('POST', '/api/v1/library/scan', (w) => {
    const added = w.unread.filter(
      (u) => !w.games.some((g) => g.system === u.system && g.name === u.name),
    )
    for (const u of added) {
      const title = u.name.replace(/ \(.*$|\.[^.]+$/g, '')
      w.games.push({
        id: w.games.length + 1,
        system: u.system,
        name: u.name,
        title,
        region: null,
        kind: 'file',
        size: u.size,
        mtime: 1_760_000_000,
        files: 1,
        state: 'pending',
        matched: false,
        confidence: null,
        igdb_id: null,
        igdb_name: null,
        year: null,
        genres: [],
        rating: null,
        votes: null,
        cover: null,
        tags: {},
      })
    }
    w.unread = []
    return job(w, 'scan', null, { added: added.length, updated: 0, removed: 0 })
  }),
  route('GET', '/api/v1/devices/{ref}/recover', (w, [ref]) => recoverList(w, String(ref))),
  route('POST', '/api/v1/devices/{ref}/recover', (w, [ref], b) => {
    const listed = recoverList(w, String(ref))
    if (listed.status !== 200) return listed
    const item = ((listed.body as Json).items as Json[]).find(
      (i) => i.system === b.system && i.name === b.name,
    )
    if (!item)
      return failedJob(
        w,
        'recover',
        String(ref),
        'dest.transfer_failed',
        `${String(b.system)}/${String(b.name)} is not something only the device holds`,
      )
    if (item.kind === 'folder')
      return failedJob(
        w,
        'recover',
        String(ref),
        'dest.transfer_failed',
        `${String(b.system)}/${String(b.name)} is a folder; only single files are recovered`,
      )
    if (w.unread.some((u) => u.system === b.system && u.name === b.name))
      return failedJob(
        w,
        'recover',
        String(ref),
        'store.would_overwrite',
        `the store already has ${String(b.system)}/${String(b.name)}; nothing was replaced`,
      )
    w.unread.push({ system: String(b.system), name: String(b.name), size: Number(item.size ?? 0) })
    return job(w, 'recover', String(ref), { placed: 1, bytes: Number(item.size ?? 0) })
  }),
  route('POST', '/api/v1/library/match', (w) => {
    const pending = w.games.filter((g) => g.state === 'pending')
    for (const g of pending) g.state = 'not_found'
    return job(w, 'match', null, { matched: 0, not_found: pending.length })
  }),
  route('POST', '/api/v1/library/covers', (w) => job(w, 'covers', null, { filled: 0 })),
  route('POST', '/api/v1/library/franchises', (w) => job(w, 'franchise', null, { proposed: 2 })),
  route('GET', '/api/v1/maintenance/{action}', (w, [action]) => {
    const counts: Record<string, [number, number]> = {
      compact: [1, 2 * MB],
      'clear-cache': [0, 0],
      'prune-covers': [3, 600_000],
      'prune-runs': [0, 0],
    }
    const c = counts[String(action)]
    if (!c) return error(422, 'request.invalid', `no maintenance action ${action}`, 'action')
    const done = w.maintained.includes(String(action))
    return {
      status: 200,
      body: { action, count: done ? 0 : c[0], bytes: done ? 0 : c[1], names: [] },
    }
  }),
  route('POST', '/api/v1/maintenance/{action}', (w, [action], b) => {
    w.maintained.push(String(action))
    return job(w, 'maintenance', null, { removed: Number(b.expected ?? 0) })
  }),
  route('GET', '/api/v1/devices', (w) => ({
    status: 200,
    body: {
      devices: w.attached.map((a) => ({
        ...a,
        profile: w.profiles.find((p) => p.ref === a.ref) ?? null,
      })),
      blocked: w.blocked,
      unreachable: w.blocked.length,
      transports: w.transports,
    },
  })),
  // The engine lists profiles by name.
  route('GET', '/api/v1/profiles', (w) => ({
    status: 200,
    body: {
      profiles: [...w.profiles].sort(
        (a, b) =>
          String(a.name).localeCompare(String(b.name)) || String(a.id).localeCompare(String(b.id)),
      ),
    },
  })),
  route('POST', '/api/v1/profiles/{id}/rename', (w, [id], b) => {
    const p = w.profiles.find((x) => x.id === id)
    if (!p) return error(404, 'profile.not_found', `no device profile ${id}`, 'device_id')
    const name = String(b.name ?? '').trim()
    if (!name)
      return error(422, 'request.invalid', 'String should have at least 1 character', 'name')
    p.name = name
    return { status: 200, body: p }
  }),
  route('POST', '/api/v1/devices/{ref}/scan', (w, [ref]) => {
    const p = w.profiles.find((x) => x.ref === ref)
    if (!p) return error(404, 'profile.not_found', 'this device has no profile yet', 'device')
    const games = (w.inventory[String(p.id)] ?? []).filter((i) => i.system !== 'bios').length
    return job(w, 'device', String(ref), { games })
  }),
  route('POST', '/api/v1/devices/{ref}/marker', (w, [ref]) => {
    const p = w.profiles.find((x) => x.ref === ref)
    if (!p) return error(404, 'profile.not_found', 'this device has no profile yet', 'device')
    return job(w, 'device', String(ref), { written: 1 })
  }),
  route('GET', '/api/v1/profiles/{id}/selection', (w, [id]) => selectionView(w, String(id))),
  route('GET', '/api/v1/profiles/{id}/inventory', (w, [id]) =>
    w.inventory[String(id)]
      ? { status: 200, body: { items: w.inventory[String(id)] } }
      : error(404, 'profile.not_found', `no device profile ${id}`),
  ),
  route('GET', '/api/v1/profiles/{id}/runs', (w, [id]) => ({
    status: 200,
    body: { runs: w.runs[String(id)] ?? [] },
  })),
  route('POST', '/api/v1/profiles/{id}/selection/games', (w, [id], b) => {
    const s = w.selections[String(id)]
    if (!s) return error(404, 'profile.not_found', `no device profile ${id}`)
    let changed = 0
    for (const gid of (b.game_ids as number[]) ?? []) {
      const g = w.games.find((x) => x.id === gid)
      if (!g) continue
      const mode = s.modes[g.system] ?? 'off'
      if (mode === 'off') {
        if (!b.include) continue
        s.modes[g.system] = 'none'
      }
      const byMode = s.modes[g.system] === 'all'
      if (selected(w, String(id), g) !== b.include) changed++
      if (b.include === byMode) delete s.overrides[String(gid)]
      else s.overrides[String(gid)] = Boolean(b.include)
    }
    return { status: 200, body: { selection: { device_id: id, ...s }, changed } }
  }),
  route('POST', '/api/v1/profiles/{id}/selection/mode', (w, [id], b) => {
    const s = w.selections[String(id)]
    if (!s) return error(404, 'profile.not_found', `no device profile ${id}`)
    s.modes[String(b.system)] = String(b.mode)
    for (const g of w.games.filter((x) => x.system === b.system)) delete s.overrides[String(g.id)]
    return selectionView(w, String(id))
  }),
  route('POST', '/api/v1/profiles/{id}/selection/clear', (w, [id]) => {
    const s = w.selections[String(id)]
    if (!s) return error(404, 'profile.not_found', `no device profile ${id}`)
    for (const k of Object.keys(s.modes)) if (s.modes[k] !== 'off') s.modes[k] = 'none'
    s.overrides = {}
    return selectionView(w, String(id))
  }),
  route('POST', '/api/v1/devices/{ref}/profile', (w, [ref], b) => {
    const found = w.attached.find((a) => a.ref === ref)
    if (!found) return error(404, 'dest.unknown_device', 'that device is not attached', 'device')
    const had = w.profiles.find((p) => p.ref === ref)
    if (had) return { status: 200, body: had }
    return {
      status: 200,
      body: makeProfile(w, found, `dev-${w.profiles.length + 1}`, String(b.name)),
    }
  }),
  route('POST', '/api/v1/devices/{ref}/adopt', (w, [ref]) => {
    const found = w.attached.find((a) => a.ref === ref)
    if (!found) return error(404, 'dest.unknown_device', 'that device is not attached', 'device')
    const had = w.profiles.find((p) => p.ref === ref)
    if (had) return { status: 200, body: had }
    if (!found.has_marker)
      return error(400, 'dest.marker_untrusted', 'the device has no marker to adopt', 'device')
    return { status: 200, body: makeProfile(w, found, 'dev-elsewhere', 'Retroid') }
  }),
  route('GET', '/api/v1/sysfiles/store', () => ({
    status: 200,
    body: {
      items: Object.entries(SYSFILES).flatMap(([system, s]) =>
        s.files.map((f) => ({
          system,
          emulator: s.emulator,
          name: f.name,
          required: f.required,
          present: true,
          size: f.size,
          verified: f.verified,
          note: '',
        })),
      ),
    },
  })),
  route('GET', '/api/v1/devices/{ref}/sysfiles', (w, [ref]) => sysReport(w, String(ref))),
  route('POST', '/api/v1/devices/{ref}/sysfiles/survey', (w, [ref]) => {
    const d = sysfilesOf(w, String(ref))
    d.surveyed = '2026-10-11T12:00:00'
    if (!d.others.length && !Object.keys(d.staged).length)
      d.others = [{ path: `${STAGE_ROOT}/gba`, name: 'old_bios.bin', kind: 'file', size: 16_384 }]
    return job(w, 'sysfiles', String(ref), { entries: 12 })
  }),
  route('POST', '/api/v1/devices/{ref}/sysfiles/{system}/stage', (w, [ref, system]) => {
    sysfilesOf(w, String(ref)).staged[String(system)] = true
    return job(w, 'sysfiles', String(ref), { placed: SYSFILES[String(system)]?.files.length ?? 0 })
  }),
  route('POST', '/api/v1/devices/{ref}/sysfiles/{system}/unstage', (w, [ref, system]) => {
    const d = sysfilesOf(w, String(ref))
    const had = Boolean(d.staged[String(system)])
    d.staged[String(system)] = false
    return job(w, 'sysfiles', String(ref), { removed: had ? 1 : 0 })
  }),
  route('POST', '/api/v1/devices/{ref}/sysfiles/remove-other', (w, [ref], b) => {
    const d = sysfilesOf(w, String(ref))
    d.others = d.others.filter((o) => !(o.path === b.path && o.name === b.name))
    return job(w, 'sysfiles', String(ref), { removed: 1 })
  }),
  route('GET', '/api/v1/devices/{ref}/plan', (w, [ref]) => plan(w, String(ref))),
  route('POST', '/api/v1/devices/{ref}/sync', (w, [ref], b) =>
    startSync(w, String(ref), b.confirm_removals),
  ),
  route('GET', '/api/v1/devices/{ref}/sync', (w, [ref]) => syncStatus(w, String(ref))),
  route('POST', '/api/v1/devices/{ref}/sync/cancel', (w, [ref]) => {
    const s = w.syncs[String(ref)]
    if (!s) return error(404, 'job.not_found', 'no sync has run on this device', 'device')
    if (s.job.state === 'running') {
      s.job.state = 'cancelled'
      s.run.state = 'cancelled'
      s.job.result = { run: Number(s.run.id), done: 0, skipped: 1 }
    }
    return { status: 200, body: s.job }
  }),
  route('GET', '/api/v1/devices/{ref}/capacity', (w, [ref]) => {
    const c = w.capacity[String(ref)]
    return c
      ? { status: 200, body: c }
      : error(404, 'dest.unknown_device', 'that device is not attached')
  }),
  route('GET', '/api/v1/jobs/{id}', (w, [id]) => {
    const j = w.jobs.find((x) => x.id === id)
    return j ? { status: 200, body: j } : error(404, 'job.not_found', `no job ${id}`)
  }),
]

/** The API's answer to one request, changing the world as the engine would. */
export function answer(w: World, method: string, path: string, body: unknown): Answer {
  if (method === 'GET' && w.failing.some((p) => path.startsWith(p)))
    return error(503, 'dest.unavailable', 'The engine did not answer.')
  for (const r of ROUTES) {
    if (r.method !== method) continue
    const m = r.pattern.exec(path)
    if (m) return r.handle(w, m.slice(1).map(decodeURIComponent), (body ?? {}) as Json)
  }
  return error(404, 'request.not_found', `no fake for ${method} ${path}`)
}

/** The world as a fetch, for the engine client inside a story. */
export function fakeFetch(w: World): typeof fetch {
  return (async (input: Request) => {
    const url = new URL(input.url)
    const text = input.method === 'GET' ? '' : await input.text()
    const a = answer(w, input.method, url.pathname, text ? JSON.parse(text) : null)
    return new Response(JSON.stringify(a.body), {
      status: a.status,
      headers: { 'content-type': 'application/json' },
    })
  }) as typeof fetch
}
