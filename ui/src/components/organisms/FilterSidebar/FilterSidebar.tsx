import type { Facet } from '../../../lib/facets/facets'
import { Checkbox } from '../../atoms/Checkbox/Checkbox'
import { Range } from '../../atoms/Range/Range'
import { ActiveChipList, type ActiveFilter } from '../../molecules/ActiveChipList/ActiveChipList'
import { FacetRow } from '../../molecules/FacetRow/FacetRow'
import { FacetSection } from '../../molecules/FacetSection/FacetSection'
import { RangeFacet, type RangeFacetProps } from '../../molecules/RangeFacet/RangeFacet'
import { SMART_LISTS, SmartListButton } from '../../molecules/SmartListButton/SmartListButton'
import styles from './FilterSidebar.module.css'

/** The headings version 1 gave each facet. */
export const FACET_TITLES: Readonly<Record<Facet, string>> = {
  system: 'System',
  genre: 'Genre',
  franchise: 'Franchise',
  theme: 'Theme',
  mode: 'Players',
  perspective: 'Perspective',
  tag: 'Other tags',
  decade: 'Decade',
  region: 'Region',
}

export type FacetView = {
  readonly facet: Facet
  readonly rows: readonly {
    readonly value: string
    readonly label: string
    readonly count: number
    readonly chosen: boolean
  }[]
  readonly hidden: number
  readonly less: boolean
  readonly collapsed: boolean
}

export type Flags = Readonly<Record<'matched' | 'selected' | 'ondevice' | 'folder', boolean>>

const FLAG_LABELS: readonly [keyof Flags, string][] = [
  ['matched', 'has cover & details'],
  ['selected', 'in selection for this device'],
  ['ondevice', 'on this device now'],
  ['folder', 'multi-file games only'],
]

export type FilterSidebarProps = {
  readonly active: readonly ActiveFilter[]
  readonly onClearAll: () => void
  readonly onSmart: (query: string) => void
  readonly rating: number
  readonly onRating: (min: number) => void
  readonly facets: readonly FacetView[]
  readonly onToggle: (facet: Facet, value: string) => void
  readonly onFold: (facet: Facet) => void
  readonly onCollapse: (facet: Facet, collapsed: boolean) => void
  readonly onClear: (facet: Facet) => void
  readonly size: Omit<RangeFacetProps, 'title'>
  readonly year: Omit<RangeFacetProps, 'title'>
  readonly flags: Flags
  readonly onFlag: (flag: keyof Flags, on: boolean) => void
  /** Without a device, the two device flags cannot apply and say so. */
  readonly device: boolean
}

/** Every way to narrow the library, in version 1's order. */
export function FilterSidebar(p: FilterSidebarProps) {
  return (
    <div className={styles.filters}>
      <ActiveChipList filters={p.active} onClearAll={p.onClearAll} />
      <section className={styles.section} aria-labelledby="smart-lists">
        <h3 id="smart-lists" className={styles.heading}>
          Smart lists
        </h3>
        {SMART_LISTS.map((s) => (
          <SmartListButton key={s.label} label={s.label} query={s.query} onApply={p.onSmart} />
        ))}
      </section>
      <section className={styles.section} aria-labelledby="rating-floor">
        <h3 id="rating-floor" className={styles.heading}>
          Rating at least {p.rating ? p.rating : 'any'}
        </h3>
        <Range
          label="Rating at least"
          hideLabel
          min={0}
          max={100}
          value={p.rating}
          valueText={p.rating ? String(p.rating) : 'any'}
          onChange={p.onRating}
        />
      </section>
      {p.facets.map((f) => (
        <FacetSection
          key={f.facet}
          title={FACET_TITLES[f.facet]}
          collapsed={f.collapsed}
          onCollapsedChange={(c) => p.onCollapse(f.facet, c)}
          chosen={f.rows.filter((r) => r.chosen).length}
          onClear={() => p.onClear(f.facet)}
          fold={{ hidden: f.hidden, less: f.less, onToggle: () => p.onFold(f.facet) }}
        >
          {f.rows.length === 0 ? (
            <span className={styles.muted}>—</span>
          ) : (
            f.rows.map((r) => (
              <FacetRow
                key={r.value}
                label={r.label}
                count={r.count}
                chosen={r.chosen}
                onToggle={() => p.onToggle(f.facet, r.value)}
              />
            ))
          )}
        </FacetSection>
      ))}
      <RangeFacet title="Size" {...p.size} />
      <RangeFacet title="Year" {...p.year} />
      <section className={styles.section} aria-labelledby="other-flags">
        <h3 id="other-flags" className={styles.heading}>
          Other
        </h3>
        {FLAG_LABELS.map(([flag, label]) => {
          const needsDevice = flag === 'selected' || flag === 'ondevice'
          return (
            <Checkbox
              key={flag}
              label={needsDevice && !p.device ? `${label} (choose a device)` : label}
              checked={p.flags[flag]}
              disabled={needsDevice && !p.device}
              onChange={(on) => p.onFlag(flag, on)}
            />
          )
        })}
      </section>
    </div>
  )
}
