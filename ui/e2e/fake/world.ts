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
  settings: Json[]
  profiles: Json[]
  attached: Json[]
  selections: Record<string, { modes: Record<string, string>; overrides: Record<string, boolean> }>
  inventory: Record<string, { system: string; name: string; kind: string; size: number | null }[]>
  runs: Record<string, Json[]>
  capacity: Record<string, { total: number; free: number }>
  jobs: Json[]
  nextJob: number
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

function setting(key: string, kind: string, value: unknown, description: string): Json {
  return {
    key,
    kind,
    value,
    default: value,
    description,
    choices: [],
    minimum: null,
    maximum: null,
    unit: '',
    restart: false,
    secret: false,
    secret_state: null,
    stored: false,
  }
}

export const THOR_REF = 'YWRiAHNlcmlhbC0x'

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
    settings: [
      setting(
        'store.root',
        'path',
        'D:\\Games\\ROMs',
        'The store: the library every device is synced from.',
      ),
      setting(
        'capacity.warn_fraction',
        'float',
        0.8,
        'Fill fraction at which the capacity meter turns to caution.',
      ),
      setting('capacity.alarm_fraction', 'float', 0.9, 'Fill fraction at which it turns to alarm.'),
      setting(
        'plan.free_space_margin',
        'int',
        512 * MB,
        'Headroom kept free on a destination after a sync.',
      ),
    ],
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
    ],
    attached: [
      { ref: THOR_REF, kind: 'adb', description: 'AYN Thor (serial-1)', has_marker: true },
    ],
    selections: { 'dev-1': { modes: { snes: 'all', gba: 'none' }, overrides: { '2': true } } },
    inventory: {
      'dev-1': [
        { system: 'snes', name: String(all[0]?.name), kind: 'file', size: all[0]?.size ?? 0 },
        { system: 'bios', name: 'scph5501.bin', kind: 'sysfile', size: 524_288 },
      ],
    },
    runs: { 'dev-1': [] },
    capacity: { [THOR_REF]: { total: 256 * 1024 * MB, free: 120 * 1024 * MB } },
    jobs: [],
    nextJob: 1,
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

function selectionView(w: World, id: string): Answer {
  const s = w.selections[id]
  return s
    ? { status: 200, body: { device_id: id, ...s } }
    : error(404, 'profile.not_found', `no device profile ${id}`, 'device_id')
}

function job(w: World, kind: string, target: string | null): Answer {
  const view = {
    id: `job-${w.nextJob++}`,
    kind,
    target,
    state: 'done',
    progress: null,
    result: { done: 1 },
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
  route('GET', '/api/v1/session', () => ({
    status: 200,
    body: { token: 'e2e-token', shell: true },
  })),
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
  route('GET', '/api/v1/settings', (w) => ({ status: 200, body: { settings: w.settings } })),
  route('GET', '/api/v1/devices', (w) => ({
    status: 200,
    body: {
      devices: w.attached.map((a) => ({
        ...a,
        profile: w.profiles.find((p) => p.ref === a.ref) ?? null,
      })),
      unreachable: 0,
    },
  })),
  route('GET', '/api/v1/profiles', (w) => ({ status: 200, body: { profiles: w.profiles } })),
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
  route('GET', '/api/v1/devices/{ref}/plan', (w, [ref]) => plan(w, String(ref))),
  route('GET', '/api/v1/devices/{ref}/capacity', (w, [ref]) => {
    const c = w.capacity[String(ref)]
    return c ? { status: 200, body: c } : error(404, 'dest.unknown', 'that device is not attached')
  }),
  route('GET', '/api/v1/jobs/{id}', (w, [id]) => {
    const j = w.jobs.find((x) => x.id === id)
    return j ? { status: 200, body: j } : error(404, 'job.not_found', `no job ${id}`)
  }),
]

/** The API's answer to one request, changing the world as the engine would. */
export function answer(w: World, method: string, path: string, body: unknown): Answer {
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
