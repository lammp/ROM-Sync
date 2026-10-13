import { describe, expect, it } from 'vitest'
import { WORDS, read, type CapacityInput, type Thresholds } from './capacity'

const GB = 2 ** 30
const settings: Thresholds = { warnFraction: 0.8, alarmFraction: 0.9, margin: GB / 2 }
const plan = (net: number, fits: boolean | null = true, peak = Math.max(net, 0)) => ({
  add: Math.max(net, 0),
  drop: 0,
  net,
  peak,
  fits,
})
const input = (free: number, p = plan(0)): CapacityInput => ({
  capacity: 100 * GB,
  free: free * GB,
  connected: true,
  selected: { n: 10, bytes: GB },
  plan: p,
})

describe('capacity', () => {
  it('has five states, each with a word', () => {
    expect(Object.keys(WORDS)).toEqual(['unknown', 'green', 'yellow', 'red', 'full'])
  })

  it('reads the level after the sync against the thresholds', () => {
    expect(read(input(50), settings).level).toBe('green')
    expect(read(input(50, plan(30 * GB)), settings).level).toBe('yellow')
    expect(read(input(50, plan(41 * GB)), settings).level).toBe('red')
  })

  it('thresholds_from_settings: the same device reads differently under other settings', () => {
    const at = input(25)
    expect(read(at, settings).level).toBe('green')
    expect(read(at, { ...settings, warnFraction: 0.7 }).level).toBe('yellow')
    expect(read(at, { ...settings, warnFraction: 0.5, alarmFraction: 0.75 }).level).toBe('red')
  })

  it('is full on the engine verdict at the peak, even when the end would fit', () => {
    const r = read(input(10, plan(5 * GB, false, 12 * GB)), settings)
    expect(r.level).toBe('full')
    if (r.level !== 'unknown') expect(r.shortBy).toBe(12 * GB + GB / 2 - 10 * GB)
  })

  it('is unknown without a capacity or a free figure', () => {
    expect(read({ ...input(5), capacity: null }, settings).level).toBe('unknown')
    expect(read({ ...input(5), free: null }, settings).level).toBe('unknown')
  })

  it('reports now and after, held to the meter', () => {
    const r = read(input(40, plan(-10 * GB)), settings)
    expect(r).toMatchObject({ pctNow: 60, pctAfter: 50, freeAfter: 50 * GB, shortBy: 0 })
    const over = read(input(1, plan(50 * GB)), settings)
    if (over.level !== 'unknown') expect(over.pctAfter).toBe(100)
  })
})
