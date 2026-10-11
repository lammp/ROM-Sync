/**
 * The device page's arithmetic, apart from React: the systems table's rows,
 * the sync's starting point, and the words for a finished sync.
 */
import type { Mode, SystemRow } from '../../../components/organisms/SystemsTable/SystemsTable'
import type { Start } from '../../../lib/progress/progress'
import type { SelectionState } from '../../../lib/selection/selection'

export type StoreSystem = {
  readonly key: string
  readonly label: string
  readonly games: number
  readonly bytes: number
}
export type Held = { readonly system: string; readonly size: number | null }
export type Plan = {
  readonly send: readonly { readonly size: number }[]
  readonly update: readonly { readonly size: number }[]
  readonly remove: readonly { readonly size: number }[]
  readonly bytes: { readonly add: number; readonly free: number | null }
}

const isBios = (system: string) => system.toLowerCase() === 'bios'

/**
 * One row per store system, in key order, then each folder the device holds
 * that the store has no system for. System files under bios are not games
 * and are not counted.
 */
export function systemRows(
  systems: readonly StoreSystem[],
  held: readonly Held[],
  selection: SelectionState | null,
  systemOf: ReadonlyMap<number, string>,
): SystemRow[] {
  const device = new Map<string, { n: number; bytes: number }>()
  for (const h of held) {
    if (isBios(h.system)) continue
    const t = device.get(h.system) ?? { n: 0, bytes: 0 }
    device.set(h.system, { n: t.n + 1, bytes: t.bytes + (h.size ?? 0) })
  }
  const overrides = new Map<string, number>()
  for (const id of Object.keys(selection?.overrides ?? {})) {
    const s = systemOf.get(Number(id))
    if (s) overrides.set(s, (overrides.get(s) ?? 0) + 1)
  }
  const mode = (key: string): Mode => {
    const m = selection?.modes[key]
    return m === 'all' || m === 'none' ? m : 'off'
  }
  const known = new Set(systems.map((s) => s.key))
  const rows: SystemRow[] = [...systems]
    .sort((a, b) => a.key.localeCompare(b.key))
    .map((s) => ({
      key: s.key,
      label: s.label,
      store: { n: s.games, bytes: s.bytes },
      device: device.get(s.key) ?? { n: 0, bytes: 0 },
      mode: mode(s.key),
      overrides: overrides.get(s.key) ?? 0,
    }))
  for (const [key, tally] of [...device].sort(([a], [b]) => a.localeCompare(b))) {
    if (!known.has(key))
      rows.push({ key, label: key, store: null, device: tally, mode: 'off', overrides: 0 })
  }
  return rows
}

/** Where the progress arithmetic starts: what the plan moves and what the device holds. */
export function startOf(plan: Plan, held: readonly Held[]): Start {
  return {
    bytesTotal: [...plan.send, ...plan.update].reduce((a, o) => a + o.size, 0),
    removesTotal: plan.remove.length,
    onDevice: held.filter((h) => !isBios(h.system)).length,
    free: plan.bytes.free,
  }
}

/** How many operations a plan holds: nothing to do is said, not started. */
export function workIn(plan: Plan): number {
  return plan.send.length + plan.update.length + plan.remove.length
}
