/**
 * Reading a device's selection (display only). The rule lives in the engine
 * (SPEC section 5) and every change goes through it; the interface only
 * reads the result to draw badges and counts: an override decides, else the
 * system's mode does, and an unmanaged system selects nothing.
 */

export type Mode = 'all' | 'none' | 'off'

export type SelectionState = {
  readonly modes: Readonly<Record<string, string>>
  readonly overrides: Readonly<Record<string, boolean>>
}

export type Selectable = { readonly id: number; readonly system: string }

export function modeOf(s: SelectionState, system: string): Mode {
  const m = s.modes[system]
  return m === 'all' || m === 'none' ? m : 'off'
}

/** Whether an override exists for this game. */
export function isOverride(s: SelectionState, g: Selectable): boolean {
  return String(g.id) in s.overrides
}

export function isSelected(s: SelectionState, g: Selectable): boolean {
  const o = s.overrides[String(g.id)]
  return o !== undefined ? o : modeOf(s, g.system) === 'all'
}

/** The key the device's inventory and a game share: system and file name. */
export function deviceKey(system: string, name: string): string {
  return `${system}\\${name}`
}

/** Games on the device, by key, leaving system files under bios out: they are not games. */
export function onDeviceKeys(
  items: readonly { readonly system: string; readonly name: string }[],
): ReadonlySet<string> {
  return new Set(
    items.filter((i) => i.system.toLowerCase() !== 'bios').map((i) => deviceKey(i.system, i.name)),
  )
}
