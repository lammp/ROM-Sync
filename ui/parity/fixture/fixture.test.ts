import { describe, expect, test } from 'vitest'
import { V1_TAG } from '../v1/v1.ts'
import { decode, encode, makeHeader, normalise } from './fixture.ts'

describe('fixture', () => {
  test('round_trips_values_json_cannot_hold', () => {
    const value = { a: [NaN, Infinity, -Infinity, -0, 1.5], b: undefined, c: null, d: 'text' }
    const back = decode(JSON.parse(JSON.stringify(encode(value)))) as typeof value
    expect(back.a[0]).toBeNaN()
    expect(back.a[1]).toBe(Infinity)
    expect(back.a[2]).toBe(-Infinity)
    expect(Object.is(back.a[3], -0)).toBe(true)
    expect(back.a[4]).toBe(1.5)
    expect('b' in back && back.b === undefined).toBe(true)
    expect(back.c).toBeNull()
    expect(back.d).toBe('text')
  })

  test('refuses_a_value_it_cannot_encode', () => {
    expect(() => encode(new Map())).toThrow(TypeError)
  })

  test('normalise_keeps_what_a_fixture_keeps', () => {
    const back = normalise({ n: [NaN, -0], s: 'x' }) as { n: number[]; s: string }
    expect(back.n[0]).toBeNaN()
    expect(Object.is(back.n[1], -0)).toBe(true)
    expect(back.s).toBe('x')
  })

  test('header_names_the_tag', () => {
    const header = makeHeader('format')
    expect(header.tag).toBe(V1_TAG)
    expect(header.commit).toMatch(/^[0-9a-f]{40}$/)
    expect(header.corpus).toBe('format')
  })
})
