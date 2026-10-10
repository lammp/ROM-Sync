/**
 * The facet corpus: filter states over the synthetic library to version 1's
 * facet lists as drawn: values, counts, order, the fold at ten, the cap at
 * sixty, chosen values kept at zero, and the more and less markers.
 */
import { join } from 'node:path'
import { normalise } from '../fixture/fixture.ts'
import { syntheticLibrary } from '../library/library.ts'
import { UI_ROOT, bootV1 } from '../v1/v1.ts'

export const FIXTURE = join(UI_ROOT, 'src/lib/facets/__fixtures__/facets.v1.json')

export type FacetState = {
  readonly name: string
  readonly q?: string
  readonly sets?: Readonly<Record<string, readonly string[]>>
  readonly ranges?: Readonly<Record<string, number | boolean | null>>
  readonly expanded?: readonly string[]
}

export const STATES: readonly FacetState[] = [
  { name: 'nothing chosen' },
  { name: 'one system', sets: { system: ['nes'] } },
  { name: 'two systems', sets: { system: ['nes', 'snes'] } },
  { name: 'system and genre', sets: { system: ['nes'], genre: ['Platform'] } },
  { name: 'a tag past the fold', sets: { tag: ['Tag 56'] } },
  { name: 'a tag past the cap', sets: { tag: ['Tag 70'] } },
  { name: 'a chosen value with no games', sets: { franchise: ['Not A Franchise'] } },
  {
    name: 'a chosen value emptied by another facet',
    sets: { system: ['arcade'], region: ['Japan'] },
  },
  { name: 'tags expanded', expanded: ['tag'] },
  {
    name: 'every facet expanded',
    expanded: [
      'system',
      'genre',
      'tag',
      'franchise',
      'theme',
      'mode',
      'perspective',
      'decade',
      'region',
    ],
  },
  { name: 'decades', sets: { decade: ['1990s', '1980s'] } },
  { name: 'regions split on commas', sets: { region: ['Europe'] } },
  { name: 'query with facets', q: 'year>1990', sets: { genre: ['Puzzle'] } },
  { name: 'ranges and flags', ranges: { yearMin: 1990, yearMax: 2005, matched: true } },
  { name: 'folders only', ranges: { folder: true } },
  { name: 'rating floor', ranges: { rating: 80 } },
  { name: 'size window', ranges: { sizeMin: 1048576, sizeMax: 1073741824 } },
  { name: 'everything filtered out', q: 'nothing-matches-this' },
]

const READ = `(function (state) {
  for (const k of Object.keys(S.f)) if (S.f[k] instanceof Set) S.f[k].clear();
  Object.assign(S.f, { sizeMin: null, sizeMax: null, yearMin: null, yearMax: null, rating: 0, matched: false, selected: false, ondevice: false, folder: false });
  S.q = state.q || '';
  for (const [k, vals] of Object.entries(state.sets || {})) for (const v of vals) S.f[k].add(v);
  Object.assign(S.f, state.ranges || {});
  FX.expanded = new Set(state.expanded || []); FX.collapsed = new Set();
  applyFilters();
  const facets = {};
  for (const facet of FACETS) {
    const body = document.querySelector('.facet[data-facet=' + facet + '] .facet-body');
    facets[facet] = Array.from(body.children).map((el) => {
      if (el.classList.contains('more')) return { more: el.dataset.more, label: el.children[0].textContent, n: el.children[1].textContent };
      if (el.classList.contains('muted')) return { empty: el.textContent };
      return { v: el.dataset.v, label: el.children[0].textContent, n: Number(el.children[1].textContent), on: el.classList.contains('on'), zero: el.classList.contains('zero') };
    });
  }
  return { shown: S.filtered.map((g) => g.id), facets };
})`

export type FacetEntry = {
  readonly v?: string
  readonly label?: string
  readonly n?: number | string
  readonly on?: boolean
  readonly zero?: boolean
  readonly more?: string
  readonly empty?: string
}
export type FacetCase = {
  readonly state: FacetState
  readonly shown: readonly number[]
  readonly facets: Readonly<Record<string, readonly FacetEntry[]>>
}

export async function captureFacets(): Promise<FacetCase[]> {
  const v1 = await bootV1({ library: syntheticLibrary() })
  try {
    const cases = STATES.map((state) => ({
      state,
      ...v1.evaluate<object>(`${READ}(${JSON.stringify(state)})`),
    }))
    if (v1.errors.length) throw new Error(`version 1 reported: ${v1.errors.join('; ')}`)
    return normalise(cases) as FacetCase[]
  } finally {
    v1.close()
  }
}

export const FACETS = { name: 'facets', fixture: FIXTURE, capture: captureFacets } as const
