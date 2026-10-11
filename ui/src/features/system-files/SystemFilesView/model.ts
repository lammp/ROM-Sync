/** The system files page's arithmetic, apart from React. */
import type { Readiness } from '../../../components/molecules/SysfileRow/SysfileRow'
import type { Requirement } from '../../../components/molecules/SysfileReqRow/SysfileReqRow'
import type {
  Staging,
  SysfilesSystem,
} from '../../../components/organisms/SysfilesDetail/SysfilesDetail'
import type { SysSystem } from '../../../queries/sysfiles/sysfiles'

export type Tally = { readonly n: number; readonly bytes: number }

/** Games the device holds, by system, leaving system files under bios out. */
export function heldBySystem(
  items: readonly { readonly system: string; readonly size: number | null }[],
): ReadonlyMap<string, Tally> {
  const out = new Map<string, Tally>()
  for (const i of items) {
    if (i.system.toLowerCase() === 'bios') continue
    const t = out.get(i.system) ?? { n: 0, bytes: 0 }
    out.set(i.system, { n: t.n + 1, bytes: t.bytes + (i.size ?? 0) })
  }
  return out
}

/** The staging root every system's folder sits in: the folder above the first. */
export function stageRoot(systems: readonly { readonly staging_folder: string }[]): string {
  const first = systems[0]?.staging_folder ?? ''
  return first.split('/').slice(0, -1).join('/')
}

const requirement = (r: SysSystem['requirements'][number]): Requirement => ({
  name: r.name,
  stagedName: r.store.staged_name,
  note: r.note,
  required: r.required,
  group: r.group !== null,
  store: { present: r.store.present, size: r.store.size, verified: r.store.verified },
  staged: r.staged as Requirement['staged'],
  installed: r.installed as Requirement['installed'],
  installedPath: r.installed_at,
})

/** One system as the detail pane draws it. */
export function detailOf(
  s: SysSystem,
  labels: Readonly<Record<string, string>>,
  inStore: ReadonlyMap<string, number>,
  held: ReadonlyMap<string, Tally>,
): SysfilesSystem {
  return {
    key: s.key,
    label: labels[s.key] ?? s.key,
    readiness: s.readiness as Readiness,
    emulator: s.emulator,
    emulatorSeen: s.emulator_seen,
    package: s.package,
    onDevice: held.get(s.key) ?? { n: 0, bytes: 0 },
    inStore: inStore.get(s.key) ?? 0,
    missing: s.missing,
    note: s.note,
    staging: s.staging as Staging,
    stagingFolder: s.staging_folder,
    stagedAny: s.staged_any,
    requirements: s.requirements.map(requirement),
  }
}
