import { describe, expect, test } from 'vitest'
import { readFixture } from '../fixture/fixture.ts'
import { FIXTURE, captureTwins, type TwinCase } from './twins.capture.ts'

const cases = (): TwinCase[] => readFixture(FIXTURE).cases as TwinCase[]
const game = (title: string, system: string): TwinCase => {
  const found = cases().find((c) => c.title === title && c.system === system)
  if (!found) throw new Error(`no ${title} on ${system}`)
  return found
}
const pairing = (a: TwinCase, b: TwinCase) => a.twins.find((t) => t.id === b.id)

describe('twins capture', () => {
  test('exact', async () => {
    const { header, cases: fixture } = readFixture(FIXTURE)
    expect(header.corpus).toBe('twins')
    expect(fixture).toEqual(await captureTwins())
    expect(pairing(game('Mega Man 2', 'nes'), game('Mega Man II', 'gb'))).toEqual({
      id: expect.any(Number),
      loose: false,
    })
    expect(pairing(game('Sonic the Hedgehog', 'md'), game('Sonic 8-bit', 'sms'))?.loose).toBe(false)
  })

  test('loose', () => {
    const majora = game("The Legend of Zelda: Majora's Mask", 'n64')
    const majora3d = game("The Legend of Zelda: Majora's Mask 3D", 'n3ds')
    expect(pairing(majora, majora3d)?.loose).toBe(true)
    expect(pairing(majora3d, majora)?.loose).toBe(true)
  })

  test('known_non_pairs', () => {
    expect(
      pairing(game('Metroid', 'nes'), game('Metroid II: Return of Samus', 'gb')),
    ).toBeUndefined()
    expect(
      pairing(game('Super Mario Bros.', 'nes'), game('Super Mario Bros. 3', 'nes')),
    ).toBeUndefined()
    const gbTetris = cases().filter((c) => c.title === 'Tetris' && c.system === 'gb')
    expect(gbTetris).toHaveLength(2)
    for (const t of gbTetris) {
      for (const x of t.twins) expect(cases().find((c) => c.id === x.id)?.system).not.toBe('gb')
    }
    // the false pair version 1 knows about is still only offered as loose
    expect(pairing(game('Earthworm Jim', 'snes'), game('Earthworm Jim 3D', 'n64'))?.loose).toBe(
      true,
    )
  })
})
