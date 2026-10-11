/** What happens to each item only a device holds, from the device's selection (SPEC section 5). */
import type { Fate, Orphan } from '../../../components/organisms/RecoverTable/RecoverTable'
import { modeOf, type SelectionState } from '../../../lib/selection/selection'

/**
 * The next sync removes an item in a store system the device manages (all or
 * none), since the store has no copy to keep it selected; it leaves alone an
 * item in a system the device does not manage, or one the store lacks.
 */
export function fateOf(
  system: string,
  selection: SelectionState | null,
  labels: Readonly<Record<string, string>>,
): Fate {
  if (!(system in labels)) return { kind: 'left', why: `${system} is not a store system` }
  if (selection && modeOf(selection, system) !== 'off') return { kind: 'removed' }
  return { kind: 'left', why: `${labels[system]} is not managed on this device` }
}

export function orphans(
  items: readonly {
    readonly system: string
    readonly name: string
    readonly kind: string
    readonly size: number | null
  }[],
  selection: SelectionState | null,
  labels: Readonly<Record<string, string>>,
): Orphan[] {
  return items.map((i) => ({ ...i, fate: fateOf(i.system, selection, labels) }))
}
