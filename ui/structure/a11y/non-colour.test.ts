/**
 * F11-S37: no state is carried by colour alone. Two checks. Over every story
 * of every component layer, each coloured mark says what it means: a lamp or
 * glyph has a name, a meter a value, a pill a word, and a dot with no name of
 * its own sits beside words. And for each component that shows a state, every
 * state reads differently to assistive technology, not only to the eye.
 */
import { render } from '@testing-library/react'
import { createElement, type ComponentType } from 'react'
import { describe, expect, it } from 'vitest'
import { Dot } from '../../src/components/atoms/Dot/Dot'
import { Lamp } from '../../src/components/atoms/Lamp/Lamp'
import { SelectionBadge } from '../../src/components/atoms/SelectionBadge/SelectionBadge'
import { TwinGlyph } from '../../src/components/atoms/TwinGlyph/TwinGlyph'
import { CapacityMeter } from '../../src/components/molecules/CapacityMeter/CapacityMeter'
import { FacetRow } from '../../src/components/molecules/FacetRow/FacetRow'
import { JobLine } from '../../src/components/molecules/JobLine/JobLine'
import { SegmentedControl } from '../../src/components/molecules/SegmentedControl/SegmentedControl'
import {
  SysfileReqRow,
  INSTALLED,
  STAGED,
} from '../../src/components/molecules/SysfileReqRow/SysfileReqRow'
import { READINESS, SysfileRow } from '../../src/components/molecules/SysfileRow/SysfileRow'
import { RUN_STATES } from '../../src/components/organisms/RunHistory/RunHistory'
import { JOB_STATES } from '../../src/components/organisms/JobsTable/JobsTable'
import { read } from '../../src/lib/capacity/capacity'
import { allStories } from './stories'

/** Everything assistive technology reads off an element: its words and its states. */
export function signature(root: Element): string {
  const parts = [root.textContent ?? '']
  for (const el of [root, ...root.querySelectorAll('*')])
    for (const a of [
      'aria-label',
      'aria-valuetext',
      'aria-valuenow',
      'aria-pressed',
      'aria-checked',
      'aria-current',
    ])
      if (el.hasAttribute(a)) parts.push(`${a}=${el.getAttribute(a)}`)
  return parts.join('|')
}

/** Coloured marks that say nothing: named marks without a name, pills without a word, bare dots alone. */
export function silent(root: Element): string[] {
  const out: string[] = []
  for (const el of root.querySelectorAll('[role="img"]'))
    if (!(el.getAttribute('aria-label') ?? '').trim()) out.push('an image with no name')
  for (const el of root.querySelectorAll('[role="meter"], [role="progressbar"]'))
    if (!el.hasAttribute('aria-valuetext') && !el.hasAttribute('aria-valuenow'))
      out.push('a meter with no value')
  for (const el of root.querySelectorAll('[class*="pill"]'))
    if (!(el.textContent ?? '').trim()) out.push('a pill with no word')
  for (const el of root.querySelectorAll('[class*="dot"][aria-hidden="true"]')) {
    const beside = (el.parentElement?.textContent ?? '').trim()
    if (!beside) out.push('a dot with no words beside it')
  }
  return out
}

/** Renders each state and returns what each one reads as. */
function readings<P extends object>(component: ComponentType<P>, states: readonly P[]): string[] {
  return states.map((props) => {
    const { container, unmount } = render(createElement(component, props))
    const s = signature(container)
    unmount()
    return s
  })
}

const distinct = (xs: readonly string[]) => new Set(xs).size === xs.length

const noop = () => undefined
const reading = (free: number, plan: { add: number; fits: boolean | null } | null) =>
  read(
    {
      capacity: 100 * 2 ** 30,
      free,
      connected: true,
      selected: { n: 1, bytes: 1 },
      plan: plan
        ? { add: plan.add, drop: 0, net: plan.add, peak: plan.add, fits: plan.fits }
        : null,
    },
    { warnFraction: 0.8, alarmFraction: 0.9, margin: 0 },
  )

describe('non-colour', () => {
  it('every coloured mark in every story says what it means', () => {
    let stories = 0
    for (const { name, Story } of allStories()) {
      const { container, unmount } = render(createElement(Story))
      expect(silent(container), name).toEqual([])
      unmount()
      stories++
    }
    expect(stories).toBeGreaterThan(100)
  })

  it('every_state_has_a_second_channel', () => {
    const cases: [string, string[]][] = [
      ['Lamp', readings(Lamp, [{ state: 'off' }, { state: 'on' }, { state: 'bad' }])],
      [
        'Dot, named',
        readings(Dot, [
          { tone: 'ok', label: 'ready' },
          { tone: 'bad', label: 'missing' },
        ]),
      ],
      [
        'SelectionBadge',
        readings(SelectionBadge, [
          { selected: false, override: false, title: 'A', device: 'Thor', onToggle: noop },
          { selected: true, override: false, title: 'A', device: 'Thor', onToggle: noop },
          { selected: true, override: true, title: 'A', device: 'Thor', onToggle: noop },
          { selected: false, override: true, title: 'A', device: 'Thor', onToggle: noop },
        ]),
      ],
      [
        'TwinGlyph',
        readings(TwinGlyph, [
          { dupe: false, label: 'Also on GBA' },
          { dupe: true, label: 'Already selected on GBA' },
        ]),
      ],
      [
        'FacetRow',
        readings(FacetRow, [
          { label: 'SNES', count: 4, chosen: false, onToggle: noop },
          { label: 'SNES', count: 4, chosen: true, onToggle: noop },
          { label: 'SNES', count: 0, chosen: false, onToggle: noop },
        ]),
      ],
      [
        'SegmentedControl',
        readings(SegmentedControl, [
          {
            label: 'Mode',
            segments: [
              { value: 'a', label: 'all' },
              { value: 'n', label: 'none' },
            ],
            value: 'a',
            onChange: noop,
          },
          {
            label: 'Mode',
            segments: [
              { value: 'a', label: 'all' },
              { value: 'n', label: 'none' },
            ],
            value: 'n',
            onChange: noop,
          },
        ]),
      ],
      [
        'CapacityMeter',
        readings(CapacityMeter, [
          { reading: { connected: false, selected: { n: 1, bytes: 1 }, level: 'unknown' } },
          { reading: reading(60 * 2 ** 30, { add: 0, fits: true }) },
          { reading: reading(25 * 2 ** 30, { add: 0, fits: true }) },
          { reading: reading(15 * 2 ** 30, { add: 0, fits: true }) },
          { reading: reading(15 * 2 ** 30, { add: 20 * 2 ** 30, fits: false }) },
        ]),
      ],
      [
        'SysfileRow',
        readings(
          SysfileRow,
          (Object.keys(READINESS) as (keyof typeof READINESS)[]).map((state) => ({
            label: 'GBA',
            state,
            count: 3,
            active: false,
            onSelect: noop,
          })),
        ),
      ],
      [
        'SysfileReqRow, staged',
        readings(
          (p: { staged: keyof typeof STAGED }) =>
            createElement(
              'table',
              null,
              createElement(
                'tbody',
                null,
                createElement(SysfileReqRow, { req: req(p.staged, 'missing') }),
              ),
            ),
          (Object.keys(STAGED) as (keyof typeof STAGED)[]).map((staged) => ({ staged })),
        ),
      ],
      [
        'SysfileReqRow, installed',
        readings(
          (p: { installed: keyof typeof INSTALLED }) =>
            createElement(
              'table',
              null,
              createElement(
                'tbody',
                null,
                createElement(SysfileReqRow, { req: req('absent', p.installed) }),
              ),
            ),
          (Object.keys(INSTALLED) as (keyof typeof INSTALLED)[]).map((installed) => ({
            installed,
          })),
        ),
      ],
      [
        'JobLine',
        readings(
          JobLine,
          (['queued', 'running', 'cancelling', 'done', 'failed', 'cancelled'] as const).map(
            (state) => ({ state, error: state === 'failed' ? 'x' : null }),
          ),
        ),
      ],
      ['run states', Object.values(RUN_STATES).map(([, word]) => word)],
      ['job states', Object.values(JOB_STATES).map(([, word]) => word)],
    ]
    for (const [name, states] of cases)
      expect(distinct(states), `${name}: ${states.join(' / ')}`).toBe(true)
  })

  it('catches a mark that says nothing, and a state told only by colour', () => {
    const { container } = render(
      createElement(
        'div',
        null,
        createElement('span', { role: 'img' }),
        createElement('span', { role: 'meter' }),
        createElement('span', { className: '_pill_x' }),
        createElement(
          'p',
          null,
          createElement('span', { className: '_dot_x', 'aria-hidden': 'true' }),
        ),
      ),
    )
    expect(silent(container)).toEqual([
      'an image with no name',
      'a meter with no value',
      'a pill with no word',
      'a dot with no words beside it',
    ])
    const told = (on: boolean) => createElement('span', { className: on ? '_on' : '_off' }, 'Thor')
    const [a, b] = [true, false].map((on) => signature(render(told(on)).container))
    expect(distinct([a ?? '', b ?? ''])).toBe(false)
  })
})

function req(staged: keyof typeof STAGED, installed: keyof typeof INSTALLED) {
  return {
    name: 'gba_bios.bin',
    stagedName: 'gba_bios.bin',
    note: '',
    required: true,
    group: false,
    store: { present: true, size: 16384, verified: true },
    staged,
    installed,
    installedPath: '',
  }
}
